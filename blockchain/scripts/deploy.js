const hre = require("hardhat");

async function main() {
  console.log("Deploying AshaVault to MST Testnet...");

  const AshaVault = await hre.ethers.getContractFactory("AshaVault");
  const vault = await AshaVault.deploy();
  await vault.waitForDeployment();

  const contractAddress = await vault.getAddress();
  console.log("--------------------------------------------------");
  console.log("✅ AshaVault deployed successfully!");
  console.log("📍 Contract Address:", contractAddress);
  console.log("🔗 Verify on Explorer: https://mstscan.com/address/" + contractAddress);
  console.log("--------------------------------------------------");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
