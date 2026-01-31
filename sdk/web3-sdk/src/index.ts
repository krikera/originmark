/**
 * OriginMark Web3 SDK
 * Blockchain integration for decentralized signature verification
 */

import { ethers, Contract, Wallet, JsonRpcProvider } from 'ethers';
import { create as createIPFS } from 'ipfs-http-client';
import { MerkleTree } from 'merkletreejs';
import SHA256 from 'crypto-js/sha256';

// Contract ABI (simplified - would be imported from compiled contract)
const ORIGINMARK_REGISTRY_ABI = [
  "function registerSignature(bytes32 contentHash, string ipfsHash, string metadata) external returns (uint256)",
  "function registerSignatureBatch(bytes32[] contentHashes, string[] ipfsHashes, string[] metadataArray) external returns (uint256[])",
  "function getSignatureByContentHash(bytes32 contentHash) external view returns (tuple(uint256 id, bytes32 contentHash, address signer, string ipfsHash, uint256 timestamp, bool isActive, uint256 batchId, string metadata))",
  "function getSignerReputation(address signer) external view returns (tuple(uint256 totalSignatures, uint256 verifiedSignatures, uint256 disputedSignatures, uint256 reputationScore, bool isVerified, string ensName, string did))",
  "function registerDID(string did) external",
  "function disputeSignature(uint256 signatureId) external",
  "function getTotalSignatures() external view returns (uint256)",
  "function getCurrentBatchId() external view returns (uint256)",
  "function finalizeBatch(bytes32 merkleRoot) external",
  "event SignatureRegistered(uint256 indexed signatureId, bytes32 indexed contentHash, address indexed signer, string ipfsHash, uint256 batchId)",
  "event DIDRegistered(address indexed signer, string did)",
  "event ReputationUpdated(address indexed signer, uint256 newScore)"
];

export interface BlockchainSignature {
  id: bigint;
  contentHash: string;
  signer: string;
  ipfsHash: string;
  timestamp: bigint;
  isActive: boolean;
  batchId: bigint;
  metadata: string;
}

export interface SignerReputation {
  totalSignatures: bigint;
  verifiedSignatures: bigint;
  disputedSignatures: bigint;
  reputationScore: bigint;
  isVerified: boolean;
  ensName: string;
  did: string;
}

export interface OriginMarkMetadata {
  author?: string;
  modelUsed?: string;
  contentType: string;
  fileName?: string;
  signatureId: string;
  publicKey: string;
  signature: string;
  timestamp: string;
}

export interface BatchAnchorResult {
  batchId: bigint;
  merkleRoot: string;
  transactionHash: string;
  signatures: string[];
}

export class OriginMarkWeb3SDK {
  private provider: JsonRpcProvider;
  private contract: Contract;
  private wallet?: Wallet;
  private ipfsClient: any;
  
  constructor(
    contractAddress: string,
    providerUrl: string,
    privateKey?: string,
    ipfsUrl: string = '/ip4/127.0.0.1/tcp/5001'
  ) {
    this.provider = new JsonRpcProvider(providerUrl);
    this.contract = new Contract(contractAddress, ORIGINMARK_REGISTRY_ABI, this.provider);
    
    if (privateKey) {
      this.wallet = new Wallet(privateKey, this.provider);
      this.contract = this.contract.connect(this.wallet);
    }
    
    // Initialize IPFS client
    this.ipfsClient = createIPFS({ url: ipfsUrl });
  }
  
  /**
   * Connect wallet for signing transactions
   */
  async connectWallet(privateKey: string): Promise<void> {
    this.wallet = new Wallet(privateKey, this.provider);
    this.contract = this.contract.connect(this.wallet);
  }
  
  /**
   * Register a single signature on the blockchain
   */
  async registerSignature(
    contentHash: string,
    ipfsHash: string,
    metadata: OriginMarkMetadata
  ): Promise<{ signatureId: bigint; transactionHash: string }> {
    if (!this.wallet) {
      throw new Error('Wallet not connected');
    }
    
    const metadataJson = JSON.stringify(metadata);
    const tx = await this.contract.registerSignature(
      contentHash,
      ipfsHash,
      metadataJson
    );
    
    const receipt = await tx.wait();
    
    // Extract signature ID from event
    const event = receipt.logs.find((log: any) => 
      log.topics[0] === ethers.id('SignatureRegistered(uint256,bytes32,address,string,uint256)')
    );
    
    let signatureId = BigInt(0);
    if (event) {
      const parsedLog = this.contract.interface.parseLog(event);
      signatureId = parsedLog?.args.signatureId;
    }
    
    return {
      signatureId,
      transactionHash: receipt.hash
    };
  }
  
  /**
   * Register multiple signatures in a batch
   */
  async registerSignatureBatch(
    contentHashes: string[],
    ipfsHashes: string[],
    metadataArray: OriginMarkMetadata[]
  ): Promise<{ signatureIds: bigint[]; transactionHash: string }> {
    if (!this.wallet) {
      throw new Error('Wallet not connected');
    }
    
    const metadataJsonArray = metadataArray.map(m => JSON.stringify(m));
    
    const tx = await this.contract.registerSignatureBatch(
      contentHashes,
      ipfsHashes,
      metadataJsonArray
    );
    
    const receipt = await tx.wait();
    
    // Extract signature IDs from events
    const signatureIds: bigint[] = [];
    for (const log of receipt.logs) {
      if (log.topics[0] === ethers.id('SignatureRegistered(uint256,bytes32,address,string,uint256)')) {
        const parsedLog = this.contract.interface.parseLog(log);
        if (parsedLog) {
          signatureIds.push(parsedLog.args.signatureId);
        }
      }
    }
    
    return {
      signatureIds,
      transactionHash: receipt.hash
    };
  }
  
  /**
   * Anchor signatures to blockchain using Merkle tree for cost optimization
   */
  async anchorSignatureBatch(signatures: string[]): Promise<BatchAnchorResult> {
    if (!this.wallet) {
      throw new Error('Wallet not connected');
    }
    
    // Create Merkle tree from signatures
    const leaves = signatures.map(sig => SHA256(sig).toString());
    const merkleTree = new MerkleTree(leaves, SHA256);
    const merkleRoot = merkleTree.getRoot().toString('hex');
    
    // Get current batch ID
    const batchId = await this.contract.getCurrentBatchId();
    
    // Finalize batch with Merkle root
    const tx = await this.contract.finalizeBatch(`0x${merkleRoot}`);
    const receipt = await tx.wait();
    
    return {
      batchId,
      merkleRoot: `0x${merkleRoot}`,
      transactionHash: receipt.hash,
      signatures
    };
  }
  
  /**
   * Verify signature exists on blockchain
   */
  async verifySignatureOnChain(contentHash: string): Promise<BlockchainSignature | null> {
    try {
      const result = await this.contract.getSignatureByContentHash(contentHash);
      
      if (result.id === BigInt(0)) {
        return null;
      }
      
      return {
        id: result.id,
        contentHash: result.contentHash,
        signer: result.signer,
        ipfsHash: result.ipfsHash,
        timestamp: result.timestamp,
        isActive: result.isActive,
        batchId: result.batchId,
        metadata: result.metadata
      };
    } catch (error) {
      console.error('Blockchain verification error:', error);
      return null;
    }
  }
  
  /**
   * Get signer reputation from blockchain
   */
  async getSignerReputation(address: string): Promise<SignerReputation> {
    const result = await this.contract.getSignerReputation(address);
    
    return {
      totalSignatures: result.totalSignatures,
      verifiedSignatures: result.verifiedSignatures,
      disputedSignatures: result.disputedSignatures,
      reputationScore: result.reputationScore,
      isVerified: result.isVerified,
      ensName: result.ensName,
      did: result.did
    };
  }
  
  /**
   * Register Decentralized Identifier (DID)
   */
  async registerDID(did: string): Promise<string> {
    if (!this.wallet) {
      throw new Error('Wallet not connected');
    }
    
    const tx = await this.contract.registerDID(did);
    const receipt = await tx.wait();
    
    return receipt.hash;
  }
  
  /**
   * Dispute a signature
   */
  async disputeSignature(signatureId: bigint): Promise<string> {
    if (!this.wallet) {
      throw new Error('Wallet not connected');
    }
    
    const tx = await this.contract.disputeSignature(signatureId);
    const receipt = await tx.wait();
    
    return receipt.hash;
  }
  
  /**
   * Store content to IPFS
   */
  async storeToIPFS(content: Uint8Array, metadata: any): Promise<string> {
    const contentWithMetadata = {
      content: Array.from(content),
      metadata: metadata,
      timestamp: new Date().toISOString()
    };
    
    const { cid } = await this.ipfsClient.add(JSON.stringify(contentWithMetadata));
    return cid.toString();
  }
  
  /**
   * Retrieve content from IPFS
   */
  async retrieveFromIPFS(ipfsHash: string): Promise<{ content: Uint8Array; metadata: any }> {
    const chunks = [];
    for await (const chunk of this.ipfsClient.cat(ipfsHash)) {
      chunks.push(chunk);
    }
    
    const data = JSON.parse(new TextDecoder().decode(Buffer.concat(chunks)));
    
    return {
      content: new Uint8Array(data.content),
      metadata: data.metadata
    };
  }
  
  /**
   * Get blockchain network info
   */
  async getNetworkInfo(): Promise<{ name: string; chainId: number }> {
    const network = await this.provider.getNetwork();
    return {
      name: network.name,
      chainId: Number(network.chainId)
    };
  }
  
  /**
   * Get contract statistics
   */
  async getContractStats(): Promise<{
    totalSignatures: bigint;
    currentBatchId: bigint;
    contractAddress: string;
  }> {
    const totalSignatures = await this.contract.getTotalSignatures();
    const currentBatchId = await this.contract.getCurrentBatchId();
    
    return {
      totalSignatures,
      currentBatchId,
      contractAddress: await this.contract.getAddress()
    };
  }
  
  /**
   * Listen for signature registration events
   */
  onSignatureRegistered(callback: (event: any) => void): void {
    this.contract.on('SignatureRegistered', callback);
  }
  
  /**
   * Listen for DID registration events
   */
  onDIDRegistered(callback: (event: any) => void): void {
    this.contract.on('DIDRegistered', callback);
  }
  
  /**
   * Listen for reputation update events
   */
  onReputationUpdated(callback: (event: any) => void): void {
    this.contract.on('ReputationUpdated', callback);
  }
  
  /**
   * Stop listening to all events
   */
  removeAllListeners(): void {
    this.contract.removeAllListeners();
  }
  
  /**
   * Create Merkle proof for signature verification
   */
  createMerkleProof(signatures: string[], targetSignature: string): string[] {
    const leaves = signatures.map(sig => SHA256(sig).toString());
    const merkleTree = new MerkleTree(leaves, SHA256);
    const targetLeaf = SHA256(targetSignature).toString();
    const proof = merkleTree.getProof(targetLeaf);
    
    return proof.map(p => p.data.toString('hex'));
  }
  
  /**
   * Verify Merkle proof
   */
  verifyMerkleProof(
    proof: string[],
    targetSignature: string,
    merkleRoot: string
  ): boolean {
    const leaves = [targetSignature];
    const merkleTree = new MerkleTree(leaves, SHA256);
    const targetLeaf = SHA256(targetSignature).toString();
    const proofBuffers = proof.map(p => Buffer.from(p, 'hex'));
    
    return merkleTree.verify(proofBuffers, targetLeaf, merkleRoot);
  }
  
  /**
   * Estimate gas cost for signature registration
   */
  async estimateRegistrationGas(
    contentHash: string,
    ipfsHash: string,
    metadata: OriginMarkMetadata
  ): Promise<bigint> {
    const metadataJson = JSON.stringify(metadata);
    return await this.contract.registerSignature.estimateGas(
      contentHash,
      ipfsHash,
      metadataJson
    );
  }
  
  /**
   * Get current gas price
   */
  async getGasPrice(): Promise<bigint> {
    const feeData = await this.provider.getFeeData();
    return feeData.gasPrice || BigInt(0);
  }
}

export default OriginMarkWeb3SDK; 