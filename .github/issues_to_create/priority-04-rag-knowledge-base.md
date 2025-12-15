---
title: "[Priority 4] RAG Knowledge Base for rugs-expert Agent"
labels: enhancement, ml, priority-high, phase-12
assignees: ""
---

## Goal
Build a queryable knowledge base of game events and patterns for LLM-powered game analysis.

## Context
Phase 11 implemented RAG event cataloging to `/home/nomad/rugs_recordings/rag_events/`. Need to structure this data for semantic search and agent queries.

## Tasks
- [ ] Design RAG schema for event types (game state, player actions, market patterns, leaderboard)
- [ ] Implement vector embedding for event similarity search
- [ ] Create query interface for rugs-expert agent
- [ ] Index existing recordings (929 games)
- [ ] Build retrieval prompts for common patterns:
  - "Show games where player bought at 10x and sold at 40x"
  - "Find games with similar volatility to game X"
  - "Identify early rug signals from historical data"
- [ ] Write integration tests
- [ ] Document query syntax and capabilities

## Success Criteria
- RAG database indexed with 929+ games
- Query API returns relevant events within 500ms
- rugs-expert agent can answer complex pattern questions
- Documentation for query syntax and capabilities
- Example queries in documentation

## Dependencies
- Priority 3 complete (20-30 game recordings)

## Related Files
- `src/services/rag_ingester.py` - Event cataloging
- `docs/plans/2025-12-14-cdp-websocket-interception-design.md` - RAG architecture
- `/home/nomad/rugs_recordings/rag_events/` - Event storage

## Estimated Effort
6-8 hours
