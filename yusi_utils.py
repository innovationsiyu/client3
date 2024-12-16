import streamlit as st
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
import os

tenant_id = st.secrets["tenant_id"]
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
vault_url = st.secrets["vault_url"]

credential = ClientSecretCredential(tenant_id, client_id, client_secret)
client = SecretClient(vault_url=vault_url, credential=credential)


def retrieve(secret_name):
    return client.get_secret(secret_name).value


YUSISTORAGE_CONNECTION_STRING = retrieve("YusiStorageConnectionString")


def upload_to_container(file_path):
    for attempt in range(3):
        try:
            blob_client = BlobServiceClient.from_connection_string(YUSISTORAGE_CONNECTION_STRING).get_blob_client("user-config", os.path.basename(file_path))
            chunk_size = 1 * 1024 * 1024
            block_ids = []
            with open(file_path, "rb") as file:
                chunks = iter(lambda: file.read(chunk_size), file.read(0))
                for i, chunk in enumerate(chunks, 1):
                    block_id = f"{i:06d}"
                    block_ids.append(block_id)
                    blob_client.stage_block(block_id=block_id, data=chunk)
                    print(f"Block {i} uploaded successfully")
                blob_client.commit_block_list(block_ids)
                print("File uploaded successfully")
                return blob_client.url
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
    print("Failed to upload file after maximum retries")
    return None
