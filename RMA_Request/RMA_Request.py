from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import pyodbc  # Für SQL Server Express
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Schlüssel für Flash-Nachrichten
app.config['UPLOAD_FOLDER'] = 'uploads'  # Ordner für Datei-Uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Verbindung zum SQL Server Express konfigurieren
def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=192.168.31.205;'
        'DATABASE=auftraege_db;'
        'UID=sa;'
        'PWD=passw;'
        'TrustServerCertificate=yes;'
    )
    return conn

# Datenbank initialisieren
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='auftraege' AND xtype='U')
        CREATE TABLE auftraege (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp NVARCHAR(50),
            name_kunde NVARCHAR(100),
            wohin_eingeschickt NVARCHAR(100),
            fehler NVARCHAR(255),
            kv BIT,
            seriennummer NVARCHAR(50),
            modell NVARCHAR(50),
            abgeschlossen BIT DEFAULT 0,
            kuerzel NVARCHAR(10),
            file_path NVARCHAR(255)
        )
    ''')
    conn.commit()
    conn.close()

# Startseite mit Formular und Liste
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Eintrag speichern
    if request.method == 'POST':
        name_kunde = request.form['name_kunde']
        wohin_eingeschickt = request.form['wohin_eingeschickt']
        fehler = request.form['fehler']
        kv = 1 if request.form.get('kv') == 'on' else 0
        seriennummer = request.form['seriennummer']
        modell = request.form['modell']
        kuerzel = request.form['kuerzel']
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Dateiupload
        file_path = None
        file = request.files.get('file')
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        cursor.execute("INSERT INTO auftraege (timestamp, name_kunde, wohin_eingeschickt, fehler, kv, seriennummer, modell, kuerzel, file_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (timestamp, name_kunde, wohin_eingeschickt, fehler, kv, seriennummer, modell, kuerzel, file_path))
        conn.commit()
        flash("Auftrag erfolgreich erstellt!", "success")
        return redirect(url_for('index'))

    # Suchfunktion
    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("SELECT * FROM auftraege WHERE abgeschlossen = 0 AND (name_kunde LIKE ? OR wohin_eingeschickt LIKE ? OR fehler LIKE ? OR seriennummer LIKE ? OR modell LIKE ?)", 
                       ('%' + search_query + '%',) * 5)
    else:
        cursor.execute("SELECT * FROM auftraege WHERE abgeschlossen = 0")
    auftraege = cursor.fetchall()

    # Historie der abgeschlossenen Aufträge
    cursor.execute("SELECT * FROM auftraege WHERE abgeschlossen = 1")
    historie = cursor.fetchall()

    conn.close()
    return render_template('index.html', auftraege=auftraege, historie=historie, search_query=search_query)

# Auftrag abschliessen
@app.route('/abschliessen/<int:auftrag_id>')
def abschliessen(auftrag_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE auftraege SET abgeschlossen = 1 WHERE id = ?", (auftrag_id,))
    conn.commit()
    conn.close()
    flash("Auftrag abgeschlossen!", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(input("Bitte den Port eingeben (Standard ist 5000): ") or 5000)
    app.run(host='0.0.0.0', port=port)
