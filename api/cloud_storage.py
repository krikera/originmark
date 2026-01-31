import os
import requests
import json
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import secrets

# Cloud storage providers
class CloudStorageProvider:
    """Base class for cloud storage providers"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.encryption_key = os.getenv('CLOUD_STORAGE_ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    async def upload_file(self, file_content: bytes, file_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a file with OriginMark signature"""
        raise NotImplementedError
    
    async def download_file(self, file_id: str) -> Dict[str, Any]:
        """Download a file and its metadata"""
        raise NotImplementedError
    
    async def list_files(self, folder_name: str = "OriginMark") -> List[Dict[str, Any]]:
        """List files in the OriginMark folder"""
        raise NotImplementedError
    
    async def refresh_access_token(self) -> str:
        """Refresh the access token"""
        raise NotImplementedError

class GoogleDriveProvider(CloudStorageProvider):
    """Google Drive storage provider"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.upload_url = "https://www.googleapis.com/upload/drive/v3/files"
    
    async def upload_file(self, file_content: bytes, file_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload file to Google Drive with metadata"""
        try:
            # Create OriginMark folder if it doesn't exist
            folder_id = await self._get_or_create_folder("OriginMark")
            
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id],
                'description': f"OriginMark signed file - {metadata.get('author', 'Unknown')}"
            }
            
            # Upload file
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Multipart upload
            boundary = f"----formdata-{secrets.token_hex(16)}"
            body = self._create_multipart_body(file_metadata, file_content, boundary)
            
            headers['Content-Type'] = f'multipart/related; boundary={boundary}'
            
            response = requests.post(
                f"{self.upload_url}?uploadType=multipart",
                headers=headers,
                data=body
            )
            
            if response.status_code == 200:
                file_info = response.json()
                
                # Upload metadata sidecar
                sidecar_name = f"{file_name}.originmark.json"
                sidecar_content = json.dumps(metadata, indent=2).encode()
                
                sidecar_metadata = {
                    'name': sidecar_name,
                    'parents': [folder_id],
                    'description': "OriginMark signature metadata"
                }
                
                sidecar_body = self._create_multipart_body(sidecar_metadata, sidecar_content, boundary)
                
                sidecar_response = requests.post(
                    f"{self.upload_url}?uploadType=multipart",
                    headers=headers,
                    data=sidecar_body
                )
                
                return {
                    'success': True,
                    'file_id': file_info['id'],
                    'file_name': file_info['name'],
                    'sidecar_id': sidecar_response.json()['id'] if sidecar_response.status_code == 200 else None,
                    'download_url': f"https://drive.google.com/file/d/{file_info['id']}/view"
                }
            else:
                return {
                    'success': False,
                    'error': f"Upload failed: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def download_file(self, file_id: str) -> Dict[str, Any]:
        """Download file from Google Drive"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            # Get file metadata
            metadata_response = requests.get(
                f"{self.base_url}/files/{file_id}",
                headers=headers
            )
            
            if metadata_response.status_code != 200:
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            # Download file content
            content_response = requests.get(
                f"{self.base_url}/files/{file_id}?alt=media",
                headers=headers
            )
            
            if content_response.status_code == 200:
                file_metadata = metadata_response.json()
                
                # Try to find and download sidecar file
                sidecar_content = None
                sidecar_name = f"{file_metadata['name']}.originmark.json"
                
                search_response = requests.get(
                    f"{self.base_url}/files",
                    headers=headers,
                    params={
                        'q': f"name='{sidecar_name}' and parents in '{file_metadata['parents'][0]}'",
                        'fields': 'files(id, name)'
                    }
                )
                
                if search_response.status_code == 200:
                    search_results = search_response.json()
                    if search_results['files']:
                        sidecar_id = search_results['files'][0]['id']
                        sidecar_response = requests.get(
                            f"{self.base_url}/files/{sidecar_id}?alt=media",
                            headers=headers
                        )
                        if sidecar_response.status_code == 200:
                            sidecar_content = json.loads(sidecar_response.content.decode())
                
                return {
                    'success': True,
                    'file_content': content_response.content,
                    'file_metadata': file_metadata,
                    'originmark_metadata': sidecar_content
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to download file content'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_files(self, folder_name: str = "OriginMark") -> List[Dict[str, Any]]:
        """List files in OriginMark folder"""
        try:
            folder_id = await self._get_or_create_folder(folder_name)
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(
                f"{self.base_url}/files",
                headers=headers,
                params={
                    'q': f"parents in '{folder_id}' and not name contains '.originmark.json'",
                    'fields': 'files(id, name, modifiedTime, size, mimeType)',
                    'orderBy': 'modifiedTime desc'
                }
            )
            
            if response.status_code == 200:
                files = response.json()['files']
                return [
                    {
                        'file_id': file['id'],
                        'name': file['name'],
                        'modified_time': file['modifiedTime'],
                        'size': file.get('size'),
                        'mime_type': file['mimeType']
                    }
                    for file in files
                ]
            else:
                return []
                
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    async def _get_or_create_folder(self, folder_name: str) -> str:
        """Get or create a folder and return its ID"""
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        # Search for existing folder
        search_response = requests.get(
            f"{self.base_url}/files",
            headers=headers,
            params={
                'q': f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                'fields': 'files(id, name)'
            }
        )
        
        if search_response.status_code == 200:
            folders = search_response.json()['files']
            if folders:
                return folders[0]['id']
        
        # Create folder if it doesn't exist
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        create_response = requests.post(
            f"{self.base_url}/files",
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            },
            json=folder_metadata
        )
        
        if create_response.status_code == 200:
            return create_response.json()['id']
        else:
            raise Exception("Failed to create folder")
    
    def _create_multipart_body(self, metadata: Dict[str, Any], content: bytes, boundary: str) -> bytes:
        """Create multipart body for file upload"""
        body = f"""--{boundary}
Content-Type: application/json; charset=UTF-8

{json.dumps(metadata)}
--{boundary}
Content-Type: application/octet-stream

""".encode()
        body += content
        body += f"\n--{boundary}--".encode()
        return body
    
    async def refresh_access_token(self) -> str:
        """Refresh Google Drive access token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise Exception("Google OAuth credentials not configured")
        
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            return self.access_token
        else:
            raise Exception(f"Failed to refresh token: {response.text}")

class DropboxProvider(CloudStorageProvider):
    """Dropbox storage provider"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.base_url = "https://api.dropboxapi.com/2"
        self.content_url = "https://content.dropboxapi.com/2"
    
    async def upload_file(self, file_content: bytes, file_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload file to Dropbox with metadata"""
        try:
            folder_path = "/OriginMark"
            file_path = f"{folder_path}/{file_name}"
            
            # Upload main file
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/octet-stream',
                'Dropbox-API-Arg': json.dumps({
                    'path': file_path,
                    'mode': 'add',
                    'autorename': True
                })
            }
            
            response = requests.post(
                f"{self.content_url}/files/upload",
                headers=headers,
                data=file_content
            )
            
            if response.status_code == 200:
                file_info = response.json()
                
                # Upload metadata sidecar
                sidecar_path = f"{folder_path}/{file_name}.originmark.json"
                sidecar_content = json.dumps(metadata, indent=2).encode()
                
                sidecar_headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/octet-stream',
                    'Dropbox-API-Arg': json.dumps({
                        'path': sidecar_path,
                        'mode': 'add',
                        'autorename': True
                    })
                }
                
                sidecar_response = requests.post(
                    f"{self.content_url}/files/upload",
                    headers=sidecar_headers,
                    data=sidecar_content
                )
                
                # Create shareable link
                link_response = requests.post(
                    f"{self.base_url}/sharing/create_shared_link_with_settings",
                    headers={
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'path': file_path
                    }
                )
                
                download_url = None
                if link_response.status_code == 200:
                    download_url = link_response.json()['url']
                
                return {
                    'success': True,
                    'file_id': file_info['id'],
                    'file_path': file_info['path_display'],
                    'sidecar_path': sidecar_response.json()['path_display'] if sidecar_response.status_code == 200 else None,
                    'download_url': download_url
                }
            else:
                return {
                    'success': False,
                    'error': f"Upload failed: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def download_file(self, file_path: str) -> Dict[str, Any]:
        """Download file from Dropbox"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Dropbox-API-Arg': json.dumps({'path': file_path})
            }
            
            # Download file content
            response = requests.post(
                f"{self.content_url}/files/download",
                headers=headers
            )
            
            if response.status_code == 200:
                file_metadata = json.loads(response.headers['Dropbox-API-Result'])
                
                # Try to download sidecar file
                sidecar_content = None
                sidecar_path = f"{file_path}.originmark.json"
                
                sidecar_headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Dropbox-API-Arg': json.dumps({'path': sidecar_path})
                }
                
                sidecar_response = requests.post(
                    f"{self.content_url}/files/download",
                    headers=sidecar_headers
                )
                
                if sidecar_response.status_code == 200:
                    sidecar_content = json.loads(sidecar_response.content.decode())
                
                return {
                    'success': True,
                    'file_content': response.content,
                    'file_metadata': file_metadata,
                    'originmark_metadata': sidecar_content
                }
            else:
                return {
                    'success': False,
                    'error': f"Download failed: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_files(self, folder_name: str = "OriginMark") -> List[Dict[str, Any]]:
        """List files in OriginMark folder"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/files/list_folder",
                headers=headers,
                json={
                    'path': f"/{folder_name}",
                    'include_media_info': True
                }
            )
            
            if response.status_code == 200:
                files_data = response.json()
                files = []
                
                for entry in files_data['entries']:
                    if entry['.tag'] == 'file' and not entry['name'].endswith('.originmark.json'):
                        files.append({
                            'file_id': entry['id'],
                            'name': entry['name'],
                            'path': entry['path_display'],
                            'modified_time': entry['client_modified'],
                            'size': entry['size']
                        })
                
                return files
            else:
                return []
                
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    async def refresh_access_token(self) -> str:
        """Refresh Dropbox access token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        app_key = os.getenv('DROPBOX_APP_KEY')
        app_secret = os.getenv('DROPBOX_APP_SECRET')
        
        if not app_key or not app_secret:
            raise Exception("Dropbox OAuth credentials not configured")
        
        response = requests.post(
            'https://api.dropboxapi.com/oauth2/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': app_key,
                'client_secret': app_secret
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            return self.access_token
        else:
            raise Exception(f"Failed to refresh token: {response.text}")

# Factory function to get the right provider
def get_cloud_storage_provider(provider: str, access_token: str, refresh_token: Optional[str] = None) -> CloudStorageProvider:
    """Factory function to get the appropriate cloud storage provider"""
    if provider.lower() == 'google_drive':
        return GoogleDriveProvider(access_token, refresh_token)
    elif provider.lower() == 'dropbox':
        return DropboxProvider(access_token, refresh_token)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# Utility functions
async def sync_signature_to_cloud(
    provider: CloudStorageProvider,
    file_content: bytes,
    file_name: str,
    signature_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Sync a signed file to cloud storage"""
    return await provider.upload_file(file_content, file_name, signature_metadata)

async def verify_from_cloud(
    provider: CloudStorageProvider,
    file_identifier: str
) -> Dict[str, Any]:
    """Download and verify a file from cloud storage"""
    download_result = await provider.download_file(file_identifier)
    
    if not download_result['success']:
        return download_result
    
    return {
        'success': True,
        'file_content': download_result['file_content'],
        'metadata': download_result['originmark_metadata'],
        'cloud_metadata': download_result['file_metadata']
    } 