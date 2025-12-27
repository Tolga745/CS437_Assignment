# SCADA Maintenance Mode Interface (Task 11)



## Features
- Devices in maintenance; lockout/tagout toggle; technician assignments
- Logs for maintenance start/end, device isolation, technician access
- File upload of log artifacts
- Monitoring page

## Projects
- Vulnerable app: `scada_maintenance_vulnerable/`

## How to Run

1. Make sure you are in the correct directory
   ```poweshell
   cd "CS437_Assignment/scada_maintenance_vulnerable"
   ```
2. Ensure the Python virtual environment is active.
   ```poweshell
   ..\.venv\Scripts\activate
   ```
2. Install requirements (Bootstrap is via CDN, Flask is declared already):
   ```powershell
   pip install -r requirements.txt
   ```
3. Build Docker:
   ```powershell
   docker build -t scada-vulnerable .
   ```
   
4. Run Docker:
   ```powershell
   docker run -p 5000:5000 scada-vulnerable
   ```
   Visit http://127.0.0.1:5000

## Vulnerabilities Demonstrated
1. CWE-1395: Dependency on Vulnerable Third-Party Component
   - Page: Devices (`/devices`)
   - Evidence: Includes jQuery 1.12.4 via CDN in `templates/devices.html` (known CVE-2019-11358).
   - Risk: DOM manipulation vulnerabilities, potential XSS gadget chain.
   - Patch: Remove legacy jQuery. Use modern, updateable components. In patched app, `include_vulnerable_jquery=False` and no jQuery 1.x is loaded.

2. CWE-1329: Reliance on Component That is Not Updateable
   - Page: Monitoring (`/monitoring`)
   - Evidence: `static/legacy_dashboard.js` is treated as a vendor-supplied, non-updateable component. It is bundled and referenced directly.
   - Why not updateable: Simulates firmware-embedded UI or a proprietary blob without a patch channel; replacing it would require device firmware upgrade or vendor release.
   - Patch: Remove dependence and render monitoring with maintainable code (`templates/monitoring_patched.html`).

3. CWE-434: Unrestricted Upload of File with Dangerous Type + Lack of Log System Protection
   - Page: Upload (`/upload`)
   - Evidence: Accepts any file type; saves with original filename; exposes files via `/uploads/<fname>`.
   - Patch: Whitelist extensions (`.txt`, `.log`, `.csv`), use `secure_filename`, store in controlled directory.

4. SQL Injection due to Blacklist-Based Keyword Filtering (at least 25 keywords)
   - Page: Logs (`/logs`)
   - Evidence: Vulnerable app removes many SQL keywords but still concatenates the query string; SQL injection remains possible.
   - Patch: Use parameterized queries with `LIKE ?`, no string concatenation.

## Files of Interest
- Vulnerable:
  - `scada_maintenance_vulnerable/app.py` — routes including vulnerable logs search and upload
  - `scada_maintenance_vulnerable/templates/devices.html` — loads jQuery 1.12.4 (CWE-1395)
  - `scada_maintenance_vulnerable/templates/monitoring.html` + `static/legacy_dashboard.js` — non-updateable component (CWE-1329)
  - `scada_maintenance_vulnerable/templates/upload.html` — unrestricted upload (CWE-434)
  - `scada_maintenance_vulnerable/templates/logs.html` — vulnerable blacklist filter and concatenation (SQLi)
