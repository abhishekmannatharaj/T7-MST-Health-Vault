require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const privateKey = (process.env.PRIVATE_KEY && process.env.PRIVATE_KEY !== "your_private_key_here")
  ? [process.env.PRIVATE_KEY.startsWith("0x") ? process.env.PRIVATE_KEY : `0x${process.env.PRIVATE_KEY}`]
  : [];

module.exports = {
  solidity: "0.8.24",
  networks: {
    mstTestnet: {
      url: process.env.MST_RPC_URL || "https://testnetrpc.mstblockchain.com",
      chainId: process.env.CHAIN_ID ? parseInt(process.env.CHAIN_ID) : 91562037,
      accounts: privateKey
    }
  }
};
