import os
import re
from flask import Flask, render_template, redirect, url_for, request, send_from_directory, flash
from werkzeug.utils import secure_filename
from database_setup import init_database, get_conn, add_log


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app():
	app = Flask(__name__)
	app.secret_key = "dev-secret"  # vulnerable app uses simple static secret
	os.makedirs(UPLOAD_DIR, exist_ok=True)
	os.makedirs(STATIC_DIR, exist_ok=True)
	init_database()

	@app.route("/")
	def index():
		return redirect(url_for("dashboard"))

	@app.route("/dashboard")
	def dashboard():
		conn = get_conn()
		cur = conn.cursor()
		cur.execute("SELECT COUNT(*) AS c FROM devices WHERE online=1")
		online = cur.fetchone()["c"]
		cur.execute("SELECT COUNT(*) AS c FROM devices WHERE online=0")
		offline = cur.fetchone()["c"]
		cur.execute("SELECT COUNT(*) AS c FROM logs WHERE type LIKE '%ticket%'")
		tickets = cur.fetchone()["c"]
		conn.close()
		status_summary = {
			"assets_online": online,
			"assets_offline": offline,
			"open_tickets": tickets,
		}
		return render_template("dashboard.html", status=status_summary)

	# Devices page (CWE-1395 via vulnerable jQuery)
	@app.route("/devices", methods=["GET", "POST"])
	def devices():
		conn = get_conn()
		try:
			cur = conn.cursor()
			if request.method == "POST":
				action = request.form.get("action")
				device_id = request.form.get("device_id")
				if action == "maintenance_on":
					cur.execute("UPDATE devices SET maintenance_mode=1 WHERE id=?", (device_id,))
					add_log("maintenance_start", device_id=device_id, details="Device placed in maintenance mode", conn=conn)
				elif action == "maintenance_off":
					cur.execute("UPDATE devices SET maintenance_mode=0 WHERE id=?", (device_id,))
					add_log("maintenance_end", device_id=device_id, details="Device released from maintenance mode", conn=conn)
				elif action == "lockout_on":
					cur.execute("UPDATE devices SET lockout_tagout=1 WHERE id=?", (device_id,))
					add_log("device_isolation", device_id=device_id, details="Lockout/Tagout applied", conn=conn)
				elif action == "lockout_off":
					cur.execute("UPDATE devices SET lockout_tagout=0 WHERE id=?", (device_id,))
					add_log("device_isolation", device_id=device_id, details="Lockout/Tagout released", conn=conn)
				conn.commit()
				flash("Device state updated", "info")
				return redirect(url_for("devices"))
			cur.execute("SELECT * FROM devices")
			devices = cur.fetchall()
			# Include vulnerable jQuery 1.12.4 in template via flag
			return render_template("devices.html", devices=devices, include_vulnerable_jquery=True)
		finally:
			conn.close()

	# Technicians page: assign technicians
	@app.route("/technicians", methods=["GET", "POST"])
	def technicians():
		conn = get_conn()
		try:
			cur = conn.cursor()
			if request.method == "POST":
				tech_id = request.form.get("tech_id")
				device_id = request.form.get("device_id") or None
				cur.execute("UPDATE technicians SET assigned_device_id=? WHERE id=?", (device_id, tech_id))
				add_log("technician_access", device_id=device_id, technician_id=tech_id, details="Technician assignment updated", conn=conn)
				conn.commit()
				flash("Technician assignment updated", "info")
				return redirect(url_for("technicians"))
			cur.execute("SELECT * FROM technicians")
			techs = cur.fetchall()
			cur.execute("SELECT * FROM devices")
			devices = cur.fetchall()
			return render_template("technicians.html", techs=techs, devices=devices)
		finally:
			conn.close()

	# Logs page with blacklist-based SQL filtering (vulnerable)
	@app.route("/logs")
	def logs():
		q = request.args.get("q", "")
		conn = get_conn()
		try:
			cur = conn.cursor()
			if q:
				# Blacklist filter of SQL keywords (vulnerable approach)
				blacklist = [
					"SELECT", "UNION", "OR", "AND", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
					"CREATE", "FROM", "WHERE", "LIKE", "GROUP", "BY", "ORDER", "HAVING", "JOIN",
					"LEFT", "RIGHT", "OUTER", "INNER", "LIMIT", "OFFSET", ";", "--", "/*", "*/",
					"XP_CMDSHELL", "SLEEP", "BENCHMARK", "CHAR", "NCHAR", "NVARCHAR", "CAST", "CONVERT",
				]
				filtered = q
				for kw in blacklist:
					# Escape regex special chars in keyword, then replace
					filtered = re.sub(re.escape(kw), "", filtered, flags=re.IGNORECASE)
				# Vulnerable concatenation prone to SQL injection despite blacklist
				sql = f"SELECT * FROM logs WHERE details LIKE '%{filtered}%' OR type LIKE '%{filtered}%'"
				try:
					cur.execute(sql)
					rows = cur.fetchall()
				except Exception as e:
					rows = []
					flash(f"Query error: {e}", "danger")
			else:
				cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100")
				rows = cur.fetchall()
			return render_template("logs.html", rows=rows, q=q)
		finally:
			conn.close()

	# Unrestricted file upload (CWE-434)
	@app.route("/upload", methods=["GET", "POST"])
	def upload():
		if request.method == "POST":
			f = request.files.get("file")
			if not f:
				flash("No file provided", "warning")
				return redirect(url_for("upload"))
			# Vulnerable: accept any filename and type
			filename = f.filename  # no secure_filename usage here intentionally
			path = os.path.join(UPLOAD_DIR, filename)
			f.save(path)
			# Log upload
			conn = get_conn()
			try:
				conn.execute(
					"INSERT INTO uploads (filename, stored_path, uploaded_at) VALUES (?, ?, datetime('now'))",
					(filename, path),
				)
				conn.commit()
			finally:
				conn.close()
			flash("File uploaded", "success")
			return redirect(url_for("upload"))
		# List uploads
		conn = get_conn()
		try:
			rows = conn.execute("SELECT * FROM uploads ORDER BY uploaded_at DESC").fetchall()
			return render_template("upload.html", uploads=rows)
		finally:
			conn.close()

	# Serve uploaded files (no type checks)
	@app.route("/uploads/<path:fname>")
	def serve_upload(fname):
		return send_from_directory(UPLOAD_DIR, fname)

	# Monitoring page using legacy non-updateable component (CWE-1329)
	@app.route("/monitoring")
	def monitoring():
		# Renders a page that depends on legacy_dashboard.js, simulating a component
		# that is vendor-supplied and cannot be updated by us.
		return render_template("monitoring.html")

	return app


if __name__ == "__main__":
	app = create_app()
	app.run(host="127.0.0.1", port=5000, debug=True)

