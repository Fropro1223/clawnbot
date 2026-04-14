# MEMORY.md - Long-Term Identity & Wisdom

This is my long-term memory, curated from daily experiences to help my human, Fırat, better and faster.

## 🟢 Core System Upgrades

### Unified Multi-Account Caching (April 2026)
- **Problem**: Persistent IP Bans (-1003) due to high-frequency polling across multiple accounts.
- **Solution**: Shifted from independent polling loops to a single centralized `global_cache_updater` thread.
- **Impact**: Dramatic reduction in API weight. Reliable trading on Account 5 (Real) without interruptions.
- **Lessons**: Sequential polling with controlled delays is superior to parallel polling for rate-limited APIs.

## 🗃️ Repository Knowledge

### Binance Webhook Yeni
- **Focus**: The primary trading brain.
- **Constraint**: Only Account 5 (Real) is currently active. Testnets (1-4) are decommissioned to save IP weight.
- **Automation**: Managed via Mac OS LaunchAgents for auto-resume on boot.
