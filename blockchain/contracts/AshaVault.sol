// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AshaVault {
    address public admin;
    uint256 public constant STIPEND_AMOUNT = 0.5 ether; // 0.5 $MSTC per task

    mapping(bytes32 => bool) public executedTasks;
    mapping(address => uint256) public workerCompletedCount;

    event TaskAnchored(address indexed worker, bytes32 indexed taskHash, uint256 stipend, uint256 timestamp);

    constructor() payable {
        admin = msg.sender;
    }

    // Allows contract to receive faucet funds
    receive() external payable {}

    // 1. Anchors the visit hash (Zero PII)
    // 2. Disburses native $MSTC credit to the ASHA worker
    function submitAndReward(address payable worker, bytes32 taskHash) external {
        require(msg.sender == admin, "Only authorized relay can record");
        require(!executedTasks[taskHash], "Task already recorded and rewarded");
        require(address(this).balance >= STIPEND_AMOUNT, "Contract pool empty, refill from faucet");

        executedTasks[taskHash] = true;
        workerCompletedCount[worker] += 1;

        (bool sent, ) = worker.call{value: STIPEND_AMOUNT}("");
        require(sent, "Transfer failed");

        emit TaskAnchored(worker, taskHash, STIPEND_AMOUNT, block.timestamp);
    }

    function isTaskProcessed(bytes32 taskHash) external view returns (bool) {
        return executedTasks[taskHash];
    }
}
