#!/usr/bin/env python3
"""
Script para subir archivos a Google Drive.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configuración
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'google-credentials.json'
FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

class GoogleDriveUploader:
    def __init__(self, credentials_file):
        """Inicializa el cliente de Google Drive."""
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES)
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def upload_file(self, file_path, folder_id=None):
        """Sube un archivo a Google Drive."""
        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name}
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        try:
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"Archivo subido: {file_name} (ID: {file.get('id')})")
            return file.get('id')
            
        except HttpError as error:
            print(f'Error al subir el archivo: {error}')
            return None

def main():
    # Verificar argumentos
    if len(sys.argv) < 3:
        print("Uso: python upload_to_drive.py <ruta_archivo> <folder_id>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    folder_id = sys.argv[2]
    
    # Verificar si el archivo existe
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe")
        sys.exit(1)
    
    # Inicializar y subir archivo
    uploader = GoogleDriveUploader(CREDENTIALS_FILE)
    uploader.upload_file(file_path, folder_id)

if __name__ == "__main__":
    main()
