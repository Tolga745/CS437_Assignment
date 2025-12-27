import os
import sqlite3
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "scada.db")


def get_conn():
	conn = sqlite3.connect(DB_PATH, timeout=10.0)
	conn.row_factory = sqlite3.Row
	# Enable WAL mode for better concurrent access
	conn.execute("PRAGMA journal_mode=WAL")
	return conn


def init_database():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	conn = get_conn()
	cur = conn.cursor()

	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS devices (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			online INTEGER NOT NULL DEFAULT 1,
			maintenance_mode INTEGER NOT NULL DEFAULT 0,
			lockout_tagout INTEGER NOT NULL DEFAULT 0
		)
		"""
	)

	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS technicians (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			assigned_device_id INTEGER,
			FOREIGN KEY (assigned_device_id) REFERENCES devices(id)
		)
		"""
	)

	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			type TEXT NOT NULL,
			device_id INTEGER,
			technician_id INTEGER,
			timestamp TEXT NOT NULL,
			details TEXT,
			FOREIGN KEY (device_id) REFERENCES devices(id),
			FOREIGN KEY (technician_id) REFERENCES technicians(id)
		)
		"""
	)

	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS uploads (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			filename TEXT NOT NULL,
			stored_path TEXT NOT NULL,
			uploaded_at TEXT NOT NULL
		)
		"""
	)

	conn.commit()

	# Seed minimal data if empty
	cur.execute("SELECT COUNT(*) AS c FROM devices")
	if cur.fetchone()["c"] == 0:
		cur.executemany(
			"INSERT INTO devices (name, online) VALUES (?, ?)",
			[
				("PLC-1", 1),
				("Pump-A", 1),
				("Valve-42", 1),
				("Compressor-X", 0),
				("Sensor-T", 1),
				("HMI-Panel", 1),
			],
		)

	cur.execute("SELECT COUNT(*) AS c FROM technicians")
	if cur.fetchone()["c"] == 0:
		cur.executemany(
			"INSERT INTO technicians (name) VALUES (?)",
			[("Alice",), ("Bob",), ("Charlie",)],
		)

	conn.commit()
	conn.close()
	return True


def add_log(log_type: str, device_id=None, technician_id=None, details: str = "", conn=None):
	"""Add a log entry. If conn is provided, use it (don't close). Otherwise create and close."""
	own_conn = False
	if conn is None:
		conn = get_conn()
		own_conn = True
	try:
		conn.execute(
			"INSERT INTO logs (type, device_id, technician_id, timestamp, details) VALUES (?, ?, ?, ?, ?)",
			(log_type, device_id, technician_id, datetime.utcnow().isoformat(), details),
		)
		if own_conn:
			conn.commit()
	finally:
		if own_conn:
			conn.close()


