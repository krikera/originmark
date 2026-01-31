import _sodium from 'libsodium-wrappers';
import { createHash } from 'crypto';
import axios, { AxiosInstance } from 'axios';
import { readFile, writeFile } from 'fs/promises';

export interface SignatureMetadata {
  author?: string;
  timestamp: string;
  content_type: 'text' | 'image';
  model_used?: string;
  file_name?: string;
  file_size?: number;
  format?: 'json' | 'c2pa';
}

export interface SignatureResult {
  id: string;
  content_hash: string;
  signature: string;
  public_key: string;
  private_key?: string;
  timestamp: string;
  metadata: SignatureMetadata;
  manifest?: any; // C2PA manifest when format is 'c2pa'
  signed_at?: string;
}

export interface C2PAResult {
  success: boolean;
  signature_id: string;
  c2pa_manifest: any;
  content_hash: string;
  signed_at: string;
}

export interface VerificationResult {
  valid: boolean;
  message: string;
  content_hash: string;
  metadata?: SignatureMetadata;
}

export class OriginMarkSDK {
  private apiClient?: AxiosInstance;
  private sodium: typeof _sodium | null = null;

  constructor(private apiUrl?: string) {
    if (apiUrl) {
      this.apiClient = axios.create({
        baseURL: apiUrl,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }
  }

  private async ensureSodium() {
    if (!this.sodium) {
      await _sodium.ready;
      this.sodium = _sodium;
    }
    return this.sodium;
  }

  private computeHash(content: Buffer | Uint8Array): string {
    const hash = createHash('sha256');
    hash.update(content);
    return hash.digest('hex');
  }

  /**
   * Sign content locally using Ed25519
   */
  async signContent(
    content: Buffer | Uint8Array | string,
    metadata?: Partial<SignatureMetadata>,
    privateKey?: string
  ): Promise<SignatureResult> {
    const sodium = await this.ensureSodium();

    // Convert string to buffer if needed
    const contentBuffer = typeof content === 'string' 
      ? Buffer.from(content, 'utf-8') 
      : content;

    // Generate or use provided key pair
    let keyPair: _sodium.KeyPair;
    if (privateKey) {
      const privateKeyBytes = sodium.from_base64(privateKey, sodium.base64_variants.ORIGINAL);
      keyPair = sodium.crypto_sign_seed_keypair(privateKeyBytes);
    } else {
      keyPair = sodium.crypto_sign_keypair();
    }

    // Compute content hash
    const contentHash = this.computeHash(contentBuffer);

    // Sign the hash
    const signature = sodium.crypto_sign_detached(
      sodium.from_string(contentHash),
      keyPair.privateKey
    );

    // Generate result
    const result: SignatureResult = {
      id: this.generateId(),
      content_hash: contentHash,
      signature: sodium.to_base64(signature, sodium.base64_variants.ORIGINAL),
      public_key: sodium.to_base64(keyPair.publicKey, sodium.base64_variants.ORIGINAL),
      private_key: privateKey ? undefined : sodium.to_base64(keyPair.privateKey, sodium.base64_variants.ORIGINAL),
      timestamp: new Date().toISOString(),
      metadata: {
        timestamp: new Date().toISOString(),
        content_type: metadata?.content_type || 'text',
        ...metadata
      }
    };

    return result;
  }

  /**
   * Verify content signature locally
   */
  async verifyContent(
    content: Buffer | Uint8Array | string,
    signature: string,
    publicKey: string
  ): Promise<VerificationResult> {
    const sodium = await this.ensureSodium();

    try {
      // Convert string to buffer if needed
      const contentBuffer = typeof content === 'string' 
        ? Buffer.from(content, 'utf-8') 
        : content;

      // Compute content hash
      const contentHash = this.computeHash(contentBuffer);

      // Convert base64 strings to Uint8Array
      const signatureBytes = sodium.from_base64(signature, sodium.base64_variants.ORIGINAL);
      const publicKeyBytes = sodium.from_base64(publicKey, sodium.base64_variants.ORIGINAL);

      // Verify signature
      const isValid = sodium.crypto_sign_verify_detached(
        signatureBytes,
        sodium.from_string(contentHash),
        publicKeyBytes
      );

      return {
        valid: isValid,
        message: isValid ? 'Signature verified successfully' : 'Invalid signature',
        content_hash: contentHash
      };
    } catch (error) {
      return {
        valid: false,
        message: `Verification failed: ${error}`,
        content_hash: ''
      };
    }
  }

  /**
   * Sign file and create sidecar JSON
   */
  async signFile(
    filePath: string,
    metadata?: Partial<SignatureMetadata>,
    privateKey?: string
  ): Promise<SignatureResult> {
    try {
      const content = await readFile(filePath);
      const fileName = filePath.split('/').pop() || filePath;
      
      const result = await this.signContent(content, {
        ...metadata,
        file_name: fileName,
        file_size: content.length,
        content_type: this.getContentType(fileName)
      }, privateKey);

      // Save sidecar JSON
      const sidecarPath = `${filePath}.originmark.json`;
      await writeFile(sidecarPath, JSON.stringify(result, null, 2));

      return result;
    } catch (error) {
      throw new Error(`Failed to sign file: ${error}`);
    }
  }

  /**
   * Verify file with sidecar JSON
   */
  async verifyFile(filePath: string, sidecarPath?: string): Promise<VerificationResult> {
    try {
      const content = await readFile(filePath);
      const sidecarFile = sidecarPath || `${filePath}.originmark.json`;
      const sidecarData = JSON.parse(await readFile(sidecarFile, 'utf-8')) as SignatureResult;

      const result = await this.verifyContent(
        content,
        sidecarData.signature,
        sidecarData.public_key
      );

      return {
        ...result,
        metadata: sidecarData.metadata
      };
    } catch (error) {
      throw new Error(`Failed to verify file: ${error}`);
    }
  }

  /**
   * Sign content using API
   */
  async signContentAPI(
    file: File | Blob,
    metadata?: Partial<SignatureMetadata>
  ): Promise<SignatureResult> {
    if (!this.apiClient) {
      throw new Error('API URL not configured');
    }

    const formData = new FormData();
    formData.append('file', file);
    if (metadata?.author) formData.append('author', metadata.author);
    if (metadata?.model_used) formData.append('model_used', metadata.model_used);

    const response = await this.apiClient.post('/sign', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    return response.data;
  }

  /**
   * Verify content using API
   */
  async verifyContentAPI(
    file: File | Blob,
    signatureId?: string,
    signature?: string,
    publicKey?: string
  ): Promise<VerificationResult> {
    if (!this.apiClient) {
      throw new Error('API URL not configured');
    }

    const formData = new FormData();
    formData.append('file', file);
    if (signatureId) formData.append('signature_id', signatureId);
    if (signature) formData.append('signature', signature);
    if (publicKey) formData.append('public_key', publicKey);

    const response = await this.apiClient.post('/verify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    return response.data;
  }

  private generateId(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  private getContentType(fileName: string): 'text' | 'image' {
    const ext = fileName.split('.').pop()?.toLowerCase();
    const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'];
    return imageExtensions.includes(ext || '') ? 'image' : 'text';
  }

  /**
   * Signs content and exports it in C2PA format
   */
  async signContentC2PA(
    content: Buffer | Uint8Array | string,
    metadata: Partial<SignatureMetadata> = {},
    privateKey?: string
  ): Promise<C2PAResult> {
    try {
      // First sign normally with C2PA format
      const signResult = await this.signContent(content, { ...metadata, format: 'c2pa' }, privateKey);
      
      // Return C2PA manifest
      return {
        success: true,
        signature_id: signResult.id,
        c2pa_manifest: signResult.manifest || {},
        content_hash: signResult.content_hash,
        signed_at: signResult.signed_at || signResult.timestamp
      };
    } catch (error) {
      console.error('C2PA signing error:', error);
      throw new Error(`C2PA signing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Exports an existing signature in C2PA format
   */
  async exportSignatureC2PA(signatureId: string): Promise<C2PAResult> {
    try {
      const response = await this.apiClient.get(`/signatures/${signatureId}/c2pa`);
      return response.data;
    } catch (error) {
      console.error('C2PA export error:', error);
      throw new Error(`C2PA export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

// Export convenience functions
export async function signContent(
  content: Buffer | Uint8Array | string,
  metadata?: Partial<SignatureMetadata>,
  privateKey?: string
): Promise<SignatureResult> {
  const sdk = new OriginMarkSDK();
  return sdk.signContent(content, metadata, privateKey);
}

export async function verifyContent(
  content: Buffer | Uint8Array | string,
  signature: string,
  publicKey: string
): Promise<VerificationResult> {
  const sdk = new OriginMarkSDK();
  return sdk.verifyContent(content, signature, publicKey);
} 