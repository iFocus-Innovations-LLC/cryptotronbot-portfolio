"""
Secure storage utilities using Google Cloud Storage and KMS encryption
"""
import json
import os
from datetime import datetime
from google.cloud import storage
from google.cloud import kms_v1
from google.auth.exceptions import GoogleAuthError

class SecureStorage:
    """Secure storage for user data using Google Cloud Storage and KMS"""
    
    def __init__(self, project_id=None, bucket_name=None, key_ring_name=None):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.bucket_name = bucket_name or os.getenv('CLOUD_STORAGE_BUCKET', 'cryptotronbot-user-data')
        self.key_ring_name = key_ring_name or os.getenv('KMS_KEY_RING', 'cryptotronbot-keys')
        self.key_name = os.getenv('KMS_KEY_NAME', 'user-data-key')
        
        try:
            self.storage_client = storage.Client()
            self.kms_client = kms_v1.KeyManagementServiceClient()
        except GoogleAuthError as e:
            raise Exception(f"Failed to initialize Google Cloud clients: {e}")
    
    def store_user_data(self, user_id, data):
        """
        Store encrypted user data in Cloud Storage
        
        Args:
            user_id (int): User ID
            data (dict): User data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"users/{user_id}/data.json"
            blob = bucket.blob(blob_name)
            
            # Add metadata
            data['last_updated'] = datetime.utcnow().isoformat()
            
            # Encrypt data before storing
            encrypted_data = self.encrypt_data(json.dumps(data))
            blob.upload_from_string(encrypted_data)
            
            # Set metadata for audit trail
            blob.metadata = {
                'user_id': str(user_id),
                'encrypted': 'true',
                'created_at': datetime.utcnow().isoformat()
            }
            blob.patch()
            
            return True
            
        except Exception as e:
            print(f"Error storing user data: {e}")
            return False
    
    def get_user_data(self, user_id):
        """
        Retrieve and decrypt user data
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Decrypted user data or None if not found
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"users/{user_id}/data.json"
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                return None
                
            encrypted_data = blob.download_as_string()
            decrypted_data = self.decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
            
        except Exception as e:
            print(f"Error retrieving user data: {e}")
            return None
    
    def delete_user_data(self, user_id):
        """
        Delete user data from Cloud Storage
        
        Args:
            user_id (int): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"users/{user_id}/data.json"
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.delete()
            
            return True
            
        except Exception as e:
            print(f"Error deleting user data: {e}")
            return False
    
    def encrypt_data(self, data):
        """
        Encrypt data using Cloud KMS
        
        Args:
            data (str): Data to encrypt
            
        Returns:
            bytes: Encrypted data
        """
        try:
            key_name = f"projects/{self.project_id}/locations/global/keyRings/{self.key_ring_name}/cryptoKeys/{self.key_name}"
            
            request = kms_v1.EncryptRequest(
                name=key_name,
                plaintext=data.encode('utf-8')
            )
            
            response = self.kms_client.encrypt(request=request)
            return response.ciphertext
            
        except Exception as e:
            print(f"Error encrypting data: {e}")
            raise
    
    def decrypt_data(self, encrypted_data):
        """
        Decrypt data using Cloud KMS
        
        Args:
            encrypted_data (bytes): Encrypted data
            
        Returns:
            str: Decrypted data
        """
        try:
            key_name = f"projects/{self.project_id}/locations/global/keyRings/{self.key_ring_name}/cryptoKeys/{self.key_name}"
            
            request = kms_v1.DecryptRequest(
                name=key_name,
                ciphertext=encrypted_data
            )
            
            response = self.kms_client.decrypt(request=request)
            return response.plaintext.decode('utf-8')
            
        except Exception as e:
            print(f"Error decrypting data: {e}")
            raise
    
    def store_api_keys(self, user_id, api_keys):
        """
        Store encrypted API keys for a user
        
        Args:
            user_id (int): User ID
            api_keys (dict): API keys to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"users/{user_id}/api_keys.json"
            blob = bucket.blob(blob_name)
            
            # Add metadata
            api_keys['last_updated'] = datetime.utcnow().isoformat()
            
            # Encrypt API keys before storing
            encrypted_data = self.encrypt_data(json.dumps(api_keys))
            blob.upload_from_string(encrypted_data)
            
            # Set metadata
            blob.metadata = {
                'user_id': str(user_id),
                'encrypted': 'true',
                'type': 'api_keys',
                'created_at': datetime.utcnow().isoformat()
            }
            blob.patch()
            
            return True
            
        except Exception as e:
            print(f"Error storing API keys: {e}")
            return False
    
    def get_api_keys(self, user_id):
        """
        Retrieve encrypted API keys for a user
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Decrypted API keys or None if not found
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob_name = f"users/{user_id}/api_keys.json"
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                return None
                
            encrypted_data = blob.download_as_string()
            decrypted_data = self.decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
            
        except Exception as e:
            print(f"Error retrieving API keys: {e}")
            return None
    
    def list_user_files(self, user_id):
        """
        List all files stored for a user
        
        Args:
            user_id (int): User ID
            
        Returns:
            list: List of file names
        """
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=f"users/{user_id}/")
            
            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created': blob.time_created.isoformat(),
                    'updated': blob.updated.isoformat()
                })
            
            return files
            
        except Exception as e:
            print(f"Error listing user files: {e}")
            return []
    
    def backup_user_data(self, user_id, backup_name=None):
        """
        Create a backup of user data
        
        Args:
            user_id (int): User ID
            backup_name (str): Optional backup name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_data = self.get_user_data(user_id)
            if not user_data:
                return False
            
            bucket = self.storage_client.bucket(self.bucket_name)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = backup_name or f"backup_{timestamp}"
            blob_name = f"users/{user_id}/backups/{backup_name}.json"
            blob = bucket.blob(blob_name)
            
            # Encrypt backup data
            encrypted_data = self.encrypt_data(json.dumps(user_data))
            blob.upload_from_string(encrypted_data)
            
            # Set metadata
            blob.metadata = {
                'user_id': str(user_id),
                'encrypted': 'true',
                'type': 'backup',
                'backup_name': backup_name,
                'created_at': datetime.utcnow().isoformat()
            }
            blob.patch()
            
            return True
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False 