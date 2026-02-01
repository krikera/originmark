'use client';

import React, { useState, useEffect, createContext, useContext } from 'react';
import { ethers } from 'ethers';

// Wallet connection types
declare global {
  interface Window {
    ethereum?: any;
  }
}

interface WalletState {
  isConnected: boolean;
  address: string | null;
  provider: ethers.BrowserProvider | null;
  signer: ethers.JsonRpcSigner | null;
  chainId: number | null;
  balance: string | null;
  ensName: string | null;
}

interface WalletContextType extends WalletState {
  connect: () => Promise<void>;
  disconnect: () => void;
  switchChain: (chainId: number) => Promise<void>;
  signMessage: (message: string) => Promise<string>;
  registerDID: (did: string) => Promise<string>;
}

// Supported networks
const SUPPORTED_NETWORKS = {
  1: { name: 'Ethereum Mainnet', rpc: 'https://mainnet.infura.io/v3/' },
  11155111: { name: 'Sepolia Testnet', rpc: 'https://sepolia.infura.io/v3/' },
  137: { name: 'Polygon', rpc: 'https://polygon-rpc.com' },
  42161: { name: 'Arbitrum', rpc: 'https://arb1.arbitrum.io/rpc' },
};

// Create wallet context
const WalletContext = createContext<WalletContextType | null>(null);

export const useWallet = () => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [walletState, setWalletState] = useState<WalletState>({
    isConnected: false,
    address: null,
    provider: null,
    signer: null,
    chainId: null,
    balance: null,
    ensName: null,
  });

  const [isConnecting, setIsConnecting] = useState(false);

  // Check if wallet is already connected on page load
  useEffect(() => {
    checkConnection();

    // Listen for account changes
    if (window.ethereum) {
      window.ethereum.on('accountsChanged', handleAccountsChanged);
      window.ethereum.on('chainChanged', handleChainChanged);
      window.ethereum.on('disconnect', handleDisconnect);
    }

    return () => {
      if (window.ethereum) {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
        window.ethereum.removeListener('chainChanged', handleChainChanged);
        window.ethereum.removeListener('disconnect', handleDisconnect);
      }
    };
  }, []);

  const checkConnection = async () => {
    if (window.ethereum) {
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const accounts = await provider.listAccounts();

        if (accounts.length > 0) {
          await updateWalletState(provider);
        }
      } catch (error) {
        console.error('Error checking wallet connection:', error);
      }
    }
  };

  const updateWalletState = async (provider: ethers.BrowserProvider) => {
    try {
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      const network = await provider.getNetwork();
      const balance = await provider.getBalance(address);

      // Try to get ENS name
      let ensName = null;
      try {
        ensName = await provider.lookupAddress(address);
      } catch (error) {
        // ENS resolution failed, that's okay
      }

      setWalletState({
        isConnected: true,
        address,
        provider,
        signer,
        chainId: Number(network.chainId),
        balance: ethers.formatEther(balance),
        ensName,
      });
    } catch (error) {
      console.error('Error updating wallet state:', error);
      setWalletState(prev => ({ ...prev, isConnected: false }));
    }
  };

  const connect = async () => {
    if (!window.ethereum) {
      alert('Please install MetaMask or another Web3 wallet');
      return;
    }

    setIsConnecting(true);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send('eth_requestAccounts', []);
      await updateWalletState(provider);
    } catch (error) {
      console.error('Error connecting wallet:', error);
      throw error;
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnect = () => {
    setWalletState({
      isConnected: false,
      address: null,
      provider: null,
      signer: null,
      chainId: null,
      balance: null,
      ensName: null,
    });
  };

  const switchChain = async (chainId: number) => {
    if (!window.ethereum) return;

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: `0x${chainId.toString(16)}` }],
      });
    } catch (error: any) {
      // If chain doesn't exist, add it
      if (error.code === 4902) {
        const network = SUPPORTED_NETWORKS[chainId as keyof typeof SUPPORTED_NETWORKS];
        if (network) {
          try {
            await window.ethereum.request({
              method: 'wallet_addEthereumChain',
              params: [{
                chainId: `0x${chainId.toString(16)}`,
                chainName: network.name,
                rpcUrls: [network.rpc],
              }],
            });
          } catch (addError) {
            console.error('Error adding chain:', addError);
            throw addError;
          }
        }
      } else {
        throw error;
      }
    }
  };

  const signMessage = async (message: string): Promise<string> => {
    if (!walletState.signer) {
      throw new Error('Wallet not connected');
    }

    try {
      const signature = await walletState.signer.signMessage(message);
      return signature;
    } catch (error) {
      console.error('Error signing message:', error);
      throw error;
    }
  };

  const registerDID = async (did: string): Promise<string> => {
    if (!walletState.signer) {
      throw new Error('Wallet not connected');
    }

    // This would interact with the OriginMark smart contract
    // For now, just return a mock transaction hash
    console.log('Registering DID:', did);
    return '0x' + Math.random().toString(16).substring(2, 66);
  };

  const handleAccountsChanged = (accounts: string[]) => {
    if (accounts.length === 0) {
      disconnect();
    } else if (walletState.provider) {
      updateWalletState(walletState.provider);
    }
  };

  const handleChainChanged = () => {
    if (walletState.provider) {
      updateWalletState(walletState.provider);
    }
  };

  const handleDisconnect = () => {
    disconnect();
  };

  const contextValue: WalletContextType = {
    ...walletState,
    connect,
    disconnect,
    switchChain,
    signMessage,
    registerDID,
  };

  return (
    <WalletContext.Provider value={contextValue}>
      {children}
    </WalletContext.Provider>
  );
};

// Wallet connection component
export const WalletConnector: React.FC = () => {
  const {
    isConnected,
    address,
    chainId,
    balance,
    ensName,
    connect,
    disconnect,
    switchChain
  } = useWallet();

  const [isExpanded, setIsExpanded] = useState(false);

  const formatAddress = (addr: string) => {
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  };

  const getNetworkName = (id: number) => {
    return SUPPORTED_NETWORKS[id as keyof typeof SUPPORTED_NETWORKS]?.name || 'Unknown Network';
  };

  if (!isConnected) {
    return (
      <button
        onClick={connect}
        className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
      >
        Connect Wallet
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2"
      >
        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
        <span>{ensName || formatAddress(address!)}</span>
      </button>

      {isExpanded && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50">
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-700">Address</label>
              <div className="text-sm text-gray-900 font-mono break-all">{address}</div>
            </div>

            {ensName && (
              <div>
                <label className="text-sm font-medium text-gray-700">ENS Name</label>
                <div className="text-sm text-gray-900">{ensName}</div>
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-gray-700">Network</label>
              <div className="text-sm text-gray-900">{getNetworkName(chainId!)}</div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Balance</label>
              <div className="text-sm text-gray-900">{parseFloat(balance!).toFixed(4)} ETH</div>
            </div>

            <div className="flex space-x-2 pt-2">
              <button
                onClick={() => switchChain(11155111)}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
              >
                Sepolia
              </button>
              <button
                onClick={() => switchChain(1)}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
              >
                Mainnet
              </button>
            </div>

            <button
              onClick={disconnect}
              className="w-full bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
            >
              Disconnect
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Blockchain signature component
export const BlockchainSignaturePanel: React.FC<{
  contentHash: string;
  onBlockchainSign: (txHash: string) => void;
}> = ({ contentHash, onBlockchainSign }) => {
  const { isConnected, address, signMessage } = useWallet();
  const [isLoading, setIsLoading] = useState(false);
  const [txHash, setTxHash] = useState<string | null>(null);

  const handleBlockchainSign = async () => {
    if (!isConnected) {
      alert('Please connect your wallet first');
      return;
    }

    setIsLoading(true);
    try {
      // Create signature message
      const message = `OriginMark signature for content hash: ${contentHash}`;
      const signature = await signMessage(message);

      // Mock blockchain transaction (in reality, would call smart contract)
      const mockTxHash = '0x' + Math.random().toString(16).substring(2, 66);
      setTxHash(mockTxHash);
      onBlockchainSign(mockTxHash);

      console.log('Blockchain signature:', {
        contentHash,
        signer: address,
        signature,
        txHash: mockTxHash
      });
    } catch (error) {
      console.error('Blockchain signing failed:', error);
      alert('Failed to sign on blockchain');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-purple-900 mb-3">
        Blockchain Registration
      </h3>

      {!isConnected ? (
        <p className="text-purple-700 mb-3">
          Connect your wallet to register this signature on the blockchain for enhanced trust and decentralized verification.
        </p>
      ) : (
        <div className="space-y-3">
          <p className="text-purple-700">
            Register this signature on the Ethereum blockchain for permanent, tamper-proof verification.
          </p>

          <div className="text-sm text-purple-600">
            <strong>Signer:</strong> {address}
          </div>

          {txHash && (
            <div className="text-sm text-green-600">
              <strong>Transaction:</strong> <span className="font-mono">{txHash}</span>
            </div>
          )}
        </div>
      )}

      <button
        onClick={handleBlockchainSign}
        disabled={!isConnected || isLoading || !!txHash}
        className={`w-full mt-3 px-4 py-2 rounded-lg font-medium transition-colors ${!isConnected || isLoading || !!txHash
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-purple-600 hover:bg-purple-700 text-white'
          }`}
      >
        {isLoading ? 'Signing...' : txHash ? 'Registered on Blockchain' : 'Register on Blockchain'}
      </button>
    </div>
  );
};

// DID registration component
export const DIDRegistration: React.FC = () => {
  const { isConnected, registerDID } = useWallet();
  const [did, setDid] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registered, setRegistered] = useState(false);

  const handleRegisterDID = async () => {
    if (!did.trim()) {
      alert('Please enter a valid DID');
      return;
    }

    setIsLoading(true);
    try {
      const txHash = await registerDID(did);
      console.log('DID registered:', { did, txHash });
      setRegistered(true);
    } catch (error) {
      console.error('DID registration failed:', error);
      alert('Failed to register DID');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isConnected) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          Decentralized Identity
        </h3>
        <p className="text-blue-700">
          Connect your wallet to register a Decentralized Identifier (DID) for enhanced identity verification.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-blue-900 mb-3">
        Register Decentralized Identity
      </h3>

      {!registered ? (
        <div className="space-y-3">
          <p className="text-blue-700 text-sm">
            Register a DID (Decentralized Identifier) to establish your identity across the decentralized web.
          </p>

          <div>
            <label className="block text-sm font-medium text-blue-900 mb-1">
              DID
            </label>
            <input
              type="text"
              value={did}
              onChange={(e) => setDid(e.target.value)}
              placeholder="did:example:123456789abcdefghi"
              className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleRegisterDID}
            disabled={isLoading || !did.trim()}
            className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${isLoading || !did.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
          >
            {isLoading ? 'Registering...' : 'Register DID'}
          </button>
        </div>
      ) : (
        <div className="text-green-700">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">DID Registered Successfully</span>
          </div>
          <p className="text-sm mt-1">Your decentralized identity has been registered on the blockchain.</p>
        </div>
      )}
    </div>
  );
};

export default WalletConnector; 