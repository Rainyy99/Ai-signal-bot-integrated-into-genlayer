# AI Signal Bot - GenLayer Integration

**AI-Powered Trading Signal Validator** on **GenLayer Testnet Bradbury**

This Intelligent Contract acts as an on-chain "AI Judge" that evaluates the quality of crypto perpetual futures trading signals using Large Language Model (LLM) analysis.

## Features

- Validates trading signals using LLM (AI)
- Analyzes RSI, EMA Trend, Signal Strength, and trader reasoning
- Returns VALID or INVALID with AI explanation
- Stores validated signals on-chain with GenLayer AI Consensus
- Supports popular pairs (BTC, ETH, SOL, etc.)

## Technology

- GenLayer Intelligent Contracts (Python)
- Equivalence Principle for AI consensus

## Quick Deploy

### Using GenLayer Studio (Recommended)
1. Go to https://studio.genlayer.com
2. Paste contracts/TradingSignal.py
3. Deploy to Testnet Bradbury
4. Connect your wallet (OKX / MetaMask)

### Using CLI
```bash
genlayer network set testnet-bradbury
genlayer deploy --contract contracts/TradingSignal.py