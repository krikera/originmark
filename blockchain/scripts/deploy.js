const { ethers, upgrades } = require("hardhat");

async function main() {
  console.log(" Deploying OriginMark Registry...");
  
  // Get the deployer account
  const [deployer] = await ethers.getSigners();
  console.log("👤 Deploying with account:", deployer.address);
  
  // Get the contract factory
  const OriginMarkRegistry = await ethers.getContractFactory("OriginMarkRegistry");
  
  // Deploy the contract with initialOwner (OpenZeppelin 5.x requirement)
  console.log("📦 Deploying contract...");
  const registry = await OriginMarkRegistry.deploy(deployer.address);
  
  await registry.waitForDeployment();
  const address = await registry.getAddress();
  
  console.log(" OriginMark Registry deployed to:", address);
  
  // Get deployment transaction
  const deploymentTx = registry.deploymentTransaction();
  if (deploymentTx) {
    console.log(" Deployment transaction hash:", deploymentTx.hash);
    console.log("⛽ Gas used:", deploymentTx.gasLimit.toString());
  }
  
  // Verify contract version
  const version = await registry.VERSION();
  console.log(" Contract version:", version);
  
  // Get network info
  const network = await ethers.provider.getNetwork();
  console.log("🌐 Network:", network.name, "(Chain ID:", network.chainId.toString() + ")");
  
  // Wait a bit before verification on testnets/mainnet
  if (network.chainId !== 31337n) {
    console.log("⏳ Waiting for block confirmations...");
    await registry.waitForDeployment();
    
    // Log verification command
    console.log("\n To verify the contract, run:");
    console.log(`npx hardhat verify --network ${network.name} ${address}`);
  }
  
  // Save deployment info
  const fs = require("fs");
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    contractAddress: address,
    deploymentTx: deploymentTx?.hash,
    timestamp: new Date().toISOString(),
    version: version,
    deployer: (await ethers.getSigners())[0].address
  };
  
  const deploymentFile = `deployments/${network.name}-deployment.json`;
  
  // Create deployments directory if it doesn't exist
  if (!fs.existsSync("deployments")) {
    fs.mkdirSync("deployments");
  }
  
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("💾 Deployment info saved to:", deploymentFile);
  
  console.log("\n🎉 Deployment completed successfully!");
  
  return {
    contract: registry,
    address: address,
    deploymentInfo: deploymentInfo
  };
}

// Handle deployment errors
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(" Deployment failed:", error);
    process.exit(1);
  }); 