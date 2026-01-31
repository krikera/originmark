// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title OriginMarkRegistry
 * @dev Decentralized registry for OriginMark digital signatures
 * @author OriginMark Team
 * @notice This contract stores cryptographic signatures for AI-generated content verification
 * @custom:security-contact security@originmark.dev
 */
contract OriginMarkRegistry is Ownable, ReentrancyGuard, Pausable {
    // Version of the contract
    string public constant VERSION = "4.0.0";
    
    // Counter for signature IDs (replacing deprecated Counters.sol)
    uint256 private _signatureIdCounter;
    
    // Counter for batch IDs
    uint256 private _batchIdCounter;
    
    // Signature structure
    struct Signature {
        uint256 id;
        bytes32 contentHash;
        address signer;
        string ipfsHash;
        uint256 timestamp;
        bool isActive;
        uint256 batchId;
        string metadata; // JSON metadata
    }
    
    // Batch structure for cost optimization
    struct SignatureBatch {
        uint256 id;
        bytes32 merkleRoot;
        uint256 timestamp;
        uint256 signatureCount;
        address submitter;
        bool isFinalized;
    }
    
    // Signer reputation structure
    struct SignerReputation {
        uint256 totalSignatures;
        uint256 verifiedSignatures;
        uint256 disputedSignatures;
        uint256 reputationScore; // Out of 1000
        bool isVerified;
        string ensName;
        string did; // Decentralized Identifier
    }
    
    // Mappings
    mapping(uint256 => Signature) public signatures;
    mapping(bytes32 => uint256) public contentHashToSignatureId;
    mapping(address => SignerReputation) public signerReputations;
    mapping(uint256 => SignatureBatch) public signatureBatches;
    mapping(string => address) public didToAddress;
    mapping(address => string) public addressToDid;
    
    // Arrays for enumeration
    uint256[] public allSignatureIds;
    address[] public allSigners;
    
    // Custom errors (gas efficient)
    error InvalidContentHash();
    error IPFSHashRequired();
    error ContentAlreadySigned();
    error NotVerifiedSigner();
    error SignatureDoesNotExist();
    error InvalidSignerAddress();
    error CannotDisputeOwnSignature();
    error DIDAlreadyRegistered();
    error AddressAlreadyHasDID();
    error InvalidDID();
    error BatchAlreadyFinalized();
    error EmptyBatch();
    error ArrayLengthMismatch();
    error InvalidBatchSize();
    error InvalidLimit();
    error OffsetOutOfBounds();
    
    // Events
    event SignatureRegistered(
        uint256 indexed signatureId,
        bytes32 indexed contentHash,
        address indexed signer,
        string ipfsHash,
        uint256 batchId
    );
    
    event BatchFinalized(
        uint256 indexed batchId,
        bytes32 merkleRoot,
        uint256 signatureCount,
        address submitter
    );
    
    event SignerVerified(address indexed signer, string ensName);
    event ReputationUpdated(address indexed signer, uint256 newScore);
    event DIDRegistered(address indexed signer, string did);
    event SignatureDisputed(uint256 indexed signatureId, address disputer);
    
    // Modifiers
    modifier onlyActiveSigner() {
        if (!signerReputations[msg.sender].isVerified && owner() != msg.sender) {
            revert NotVerifiedSigner();
        }
        _;
    }
    
    modifier validSignatureId(uint256 signatureId) {
        if (signatures[signatureId].id == 0) {
            revert SignatureDoesNotExist();
        }
        _;
    }
    
    /**
     * @dev Constructor - initializes the contract with the deployer as owner
     * @param initialOwner Address of the initial contract owner
     */
    constructor(address initialOwner) Ownable(initialOwner) {
        // Initialize first batch
        _batchIdCounter = 1;
    }
    
    /**
     * @dev Register a single signature
     * @param contentHash Hash of the content
     * @param ipfsHash IPFS hash for content storage
     * @param metadata JSON metadata string
     * @return signatureId The ID of the newly created signature
     */
    function registerSignature(
        bytes32 contentHash,
        string calldata ipfsHash,
        string calldata metadata
    ) external onlyActiveSigner nonReentrant whenNotPaused returns (uint256) {
        if (contentHash == bytes32(0)) revert InvalidContentHash();
        if (bytes(ipfsHash).length == 0) revert IPFSHashRequired();
        if (contentHashToSignatureId[contentHash] != 0) revert ContentAlreadySigned();
        
        unchecked {
            _signatureIdCounter++;
        }
        uint256 signatureId = _signatureIdCounter;
        uint256 currentBatchId = _batchIdCounter;
        
        signatures[signatureId] = Signature({
            id: signatureId,
            contentHash: contentHash,
            signer: msg.sender,
            ipfsHash: ipfsHash,
            timestamp: block.timestamp,
            isActive: true,
            batchId: currentBatchId,
            metadata: metadata
        });
        
        contentHashToSignatureId[contentHash] = signatureId;
        allSignatureIds.push(signatureId);
        
        // Update signer reputation
        if (signerReputations[msg.sender].totalSignatures == 0) {
            allSigners.push(msg.sender);
            signerReputations[msg.sender] = SignerReputation({
                totalSignatures: 1,
                verifiedSignatures: 0,
                disputedSignatures: 0,
                reputationScore: 500, // Start with neutral score
                isVerified: false,
                ensName: "",
                did: ""
            });
        } else {
            unchecked {
                signerReputations[msg.sender].totalSignatures++;
            }
        }
        
        // Update batch
        unchecked {
            signatureBatches[currentBatchId].signatureCount++;
        }
        
        emit SignatureRegistered(signatureId, contentHash, msg.sender, ipfsHash, currentBatchId);
        
        return signatureId;
    }
    
    /**
     * @dev Register multiple signatures in batch
     * @param contentHashes Array of content hashes
     * @param ipfsHashes Array of IPFS hashes
     * @param metadataArray Array of metadata strings
     * @return signatureIds Array of created signature IDs
     */
    function registerSignatureBatch(
        bytes32[] calldata contentHashes,
        string[] calldata ipfsHashes,
        string[] calldata metadataArray
    ) external onlyActiveSigner nonReentrant whenNotPaused returns (uint256[] memory) {
        uint256 length = contentHashes.length;
        if (length != ipfsHashes.length || length != metadataArray.length) {
            revert ArrayLengthMismatch();
        }
        if (length == 0 || length > 100) revert InvalidBatchSize();
        
        uint256[] memory signatureIds = new uint256[](length);
        uint256 currentBatchId = _batchIdCounter;
        
        for (uint256 i = 0; i < length;) {
            if (contentHashes[i] == bytes32(0)) revert InvalidContentHash();
            if (bytes(ipfsHashes[i]).length == 0) revert IPFSHashRequired();
            if (contentHashToSignatureId[contentHashes[i]] != 0) revert ContentAlreadySigned();
            
            unchecked {
                _signatureIdCounter++;
            }
            uint256 signatureId = _signatureIdCounter;
            
            signatures[signatureId] = Signature({
                id: signatureId,
                contentHash: contentHashes[i],
                signer: msg.sender,
                ipfsHash: ipfsHashes[i],
                timestamp: block.timestamp,
                isActive: true,
                batchId: currentBatchId,
                metadata: metadataArray[i]
            });
            
            contentHashToSignatureId[contentHashes[i]] = signatureId;
            allSignatureIds.push(signatureId);
            signatureIds[i] = signatureId;
            
            emit SignatureRegistered(signatureId, contentHashes[i], msg.sender, ipfsHashes[i], currentBatchId);
            
            unchecked { ++i; }
        }
        
        // Update signer reputation
        if (signerReputations[msg.sender].totalSignatures == 0) {
            allSigners.push(msg.sender);
            signerReputations[msg.sender] = SignerReputation({
                totalSignatures: length,
                verifiedSignatures: 0,
                disputedSignatures: 0,
                reputationScore: 500,
                isVerified: false,
                ensName: "",
                did: ""
            });
        } else {
            unchecked {
                signerReputations[msg.sender].totalSignatures += length;
            }
        }
        
        // Update batch
        unchecked {
            signatureBatches[currentBatchId].signatureCount += length;
        }
        
        return signatureIds;
    }
    
    /**
     * @dev Finalize current batch and create new one
     * @param merkleRoot Merkle root of the batch
     */
    function finalizeBatch(bytes32 merkleRoot) external onlyOwner {
        uint256 currentBatchId = _batchIdCounter;
        if (signatureBatches[currentBatchId].isFinalized) revert BatchAlreadyFinalized();
        if (signatureBatches[currentBatchId].signatureCount == 0) revert EmptyBatch();
        
        signatureBatches[currentBatchId] = SignatureBatch({
            id: currentBatchId,
            merkleRoot: merkleRoot,
            timestamp: block.timestamp,
            signatureCount: signatureBatches[currentBatchId].signatureCount,
            submitter: msg.sender,
            isFinalized: true
        });
        
        unchecked {
            _batchIdCounter++;
        }
        
        emit BatchFinalized(currentBatchId, merkleRoot, signatureBatches[currentBatchId].signatureCount, msg.sender);
    }
    
    /**
     * @dev Register DID for a signer
     * @param did Decentralized Identifier
     */
    function registerDID(string calldata did) external {
        if (bytes(did).length == 0) revert InvalidDID();
        if (didToAddress[did] != address(0)) revert DIDAlreadyRegistered();
        if (bytes(addressToDid[msg.sender]).length != 0) revert AddressAlreadyHasDID();
        
        didToAddress[did] = msg.sender;
        addressToDid[msg.sender] = did;
        signerReputations[msg.sender].did = did;
        
        emit DIDRegistered(msg.sender, did);
    }
    
    /**
     * @dev Verify a signer (only owner)
     * @param signer Address of the signer
     * @param ensName ENS name for the signer
     */
    function verifySigner(address signer, string calldata ensName) external onlyOwner {
        if (signer == address(0)) revert InvalidSignerAddress();
        
        signerReputations[signer].isVerified = true;
        signerReputations[signer].ensName = ensName;
        signerReputations[signer].reputationScore = 750; // Boost for verification
        
        emit SignerVerified(signer, ensName);
    }
    
    /**
     * @dev Dispute a signature
     * @param signatureId ID of the signature to dispute
     */
    function disputeSignature(uint256 signatureId) external validSignatureId(signatureId) {
        if (signatures[signatureId].signer == msg.sender) revert CannotDisputeOwnSignature();
        
        address signer = signatures[signatureId].signer;
        unchecked {
            signerReputations[signer].disputedSignatures++;
        }
        
        // Reduce reputation score
        uint256 currentScore = signerReputations[signer].reputationScore;
        signerReputations[signer].reputationScore = currentScore > 50 ? currentScore - 50 : 0;
        
        emit SignatureDisputed(signatureId, msg.sender);
        emit ReputationUpdated(signer, signerReputations[signer].reputationScore);
    }
    
    /**
     * @dev Get signature by content hash
     * @param contentHash Hash of the content
     * @return The signature data
     */
    function getSignatureByContentHash(bytes32 contentHash) external view returns (Signature memory) {
        uint256 signatureId = contentHashToSignatureId[contentHash];
        if (signatureId == 0) revert SignatureDoesNotExist();
        return signatures[signatureId];
    }
    
    /**
     * @dev Get signatures by signer with pagination
     * @param signer Address of the signer
     * @param offset Starting index
     * @param limit Maximum number of results
     * @return Array of signatures
     */
    function getSignaturesBySigner(
        address signer,
        uint256 offset,
        uint256 limit
    ) external view returns (Signature[] memory) {
        if (limit == 0 || limit > 100) revert InvalidLimit();
        
        uint256 count = 0;
        uint256 totalSignatures = allSignatureIds.length;
        
        for (uint256 i = 0; i < totalSignatures;) {
            if (signatures[allSignatureIds[i]].signer == signer) {
                unchecked { count++; }
            }
            unchecked { ++i; }
        }
        
        if (offset >= count) revert OffsetOutOfBounds();
        
        uint256 resultSize = (offset + limit > count) ? count - offset : limit;
        Signature[] memory result = new Signature[](resultSize);
        
        uint256 found = 0;
        uint256 resultIndex = 0;
        
        for (uint256 i = 0; i < totalSignatures && resultIndex < resultSize;) {
            if (signatures[allSignatureIds[i]].signer == signer) {
                if (found >= offset) {
                    result[resultIndex] = signatures[allSignatureIds[i]];
                    unchecked { resultIndex++; }
                }
                unchecked { found++; }
            }
            unchecked { ++i; }
        }
        
        return result;
    }
    
    /**
     * @dev Get total number of signatures
     * @return Total signature count
     */
    function getTotalSignatures() external view returns (uint256) {
        return allSignatureIds.length;
    }
    
    /**
     * @dev Get total number of signers
     * @return Total signer count
     */
    function getTotalSigners() external view returns (uint256) {
        return allSigners.length;
    }
    
    /**
     * @dev Get current batch ID
     * @return Current batch ID
     */
    function getCurrentBatchId() external view returns (uint256) {
        return _batchIdCounter;
    }
    
    /**
     * @dev Emergency pause - stops signature registration
     * Can only be called by the contract owner
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause the contract - resumes signature registration
     * Can only be called by the contract owner
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Get signer reputation
     * @param signer Address of the signer
     * @return SignerReputation struct
     */
    function getSignerReputation(address signer) external view returns (SignerReputation memory) {
        return signerReputations[signer];
    }
}