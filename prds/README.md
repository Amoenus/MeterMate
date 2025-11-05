# MeterMate PRD Index

> **📋 Document Type**: Navigation & Overview
> **🎯 Purpose**: Central index for all focused PRD documents
> **📅 Last Updated**: 2025-11-05

---

## About This Index

This index provides navigation across all MeterMate Product Requirement Documents (PRDs), organized following the **LLM-First Operations Model** with focused, granular files optimized for token efficiency and parallel reading.

### Document Philosophy

Each PRD file follows these principles:
- ✅ **Focused**: One topic per file (100-500 lines)
- ✅ **Independent**: Can be read standalone with cross-references
- ✅ **Actionable**: Contains concrete implementation guidance
- ✅ **LLM-Optimized**: Clear structure, explicit tool hints, decision criteria

### How to Use This Index

1. **Start here** for overview and navigation
2. **Read 2-3 focused files** for your specific task
3. **Follow cross-references** for related context
4. **Use semantic_search** for specific queries across all PRDs

---

## Phase Overview

### Phase 1: Core Improvements & Validation Patterns
**Status**: 📋 Planned
**Priority**: 🔴 CRITICAL
**Timeline**: 1-2 weeks
**Goal**: Adopt industry-standard validation and error handling patterns

**Core Focus**:
- Voluptuous schema validation
- Custom validators for MeterMate domain
- Comprehensive exception hierarchy
- Standardized error handling
- Type safety and documentation

### Phase 2: Service Architecture Enhancement
**Status**: 📋 Planned
**Priority**: 🟡 HIGH
**Timeline**: 2-3 weeks
**Dependencies**: Phase 1 completion
**Goal**: Modular service architecture with proper separation of concerns

**Core Focus**:
- Service base class hierarchy
- Category separation (query/mutation/admin)
- Centralized schema management
- Service discovery and registration
- Independent testability

### Phase 3: Optional Advanced Features
**Status**: 📋 Planned (Optional)
**Priority**: 🟢 MEDIUM/LOW
**Timeline**: 3-4 weeks (if implemented)
**Dependencies**: Phase 1 & 2 completion
**Goal**: Optional enhancements for better UX and HA integration

**Core Focus**:
- Entity registry integration
- Diagnostic sensors
- Repair detection
- Config flow enhancements
- Panel improvements

---

## Phase 1 Documents

### Core Implementation

#### [Validation Patterns](phase-1/validation-patterns.md)
**Lines**: ~300
**Focus**: Voluptuous schemas, custom validators, validation philosophy

**Key Topics**:
- Enhanced schema patterns
- Custom validator library (`validators.py`)
- Validation by service type
- Cross-field validation
- Testing strategies

**When to Read**: Implementing input validation for services

---

#### [Error Handling Patterns](phase-1/error-handling-patterns.md)
**Lines**: ~250
**Focus**: Exception hierarchy, error handling standards, logging

**Key Topics**:
- Complete exception hierarchy (`exceptions.py`)
- Service error handling patterns
- Error handling by service type (query/mutation/admin)
- Logging guidelines
- Error recovery strategies

**When to Read**: Implementing service error handling

---

#### [Phase 1 Migration Guide](phase-1/migration-guide.md)
**Lines**: ~250
**Focus**: Implementation timeline, testing strategy, success criteria

**Key Topics**:
- Day-by-day implementation plan
- Testing strategy and coverage targets
- Migration path (non-breaking)
- Validation checkpoints
- Risk management

**When to Read**: Planning Phase 1 implementation or checking progress

---

### Reference (To Be Created)

#### Service Organization Strategy
**Status**: 📝 To be extracted from original
**Lines**: ~300 (estimated)
**Focus**: Modular service file structure, organization patterns

#### Type Safety & Documentation Standards
**Status**: 📝 To be extracted from original
**Lines**: ~200 (estimated)
**Focus**: Type hints, TypedDicts, docstring standards

---

## Phase 2 Documents (To Be Created)

### Core Implementation

#### Service Base Classes
**Status**: 📝 To be created
**Lines**: ~300 (estimated)
**Focus**: Abstract base classes, inheritance hierarchy, helper methods

**Key Topics**:
- `AbstractMeterMateService` design
- Query/Mutation/Admin base classes
- Helper method patterns
- Registration methods

**When to Read**: Designing or implementing service base classes

---

#### Service Categorization
**Status**: 📝 To be created
**Lines**: ~250 (estimated)
**Focus**: Query vs mutation vs admin services, registration patterns

**Key Topics**:
- Category definitions
- Admin service registration
- Permission patterns
- Service discovery

**When to Read**: Understanding service types or implementing new services

---

#### Service Schema Management
**Status**: 📝 To be created
**Lines**: ~200 (estimated)
**Focus**: Centralized schemas, schema patterns, reusability

**Key Topics**:
- `services/schemas.py` organization
- Schema composition patterns
- Schema reuse strategies
- Documentation patterns

**When to Read**: Creating or updating service schemas

---

#### Service Module Structure
**Status**: 📝 To be created
**Lines**: ~300 (estimated)
**Focus**: Directory layout, individual services, file organization

**Key Topics**:
- `services/` directory structure
- Individual service implementation examples
- Module organization (queries/mutations/admin)
- Service README

**When to Read**: Implementing modular service architecture

---

#### Phase 2 Migration Guide
**Status**: 📝 To be created
**Lines**: ~250 (estimated)
**Focus**: Migration strategy, checkpoints, backward compatibility

**Key Topics**:
- Week-by-week migration plan
- Service migration order
- Compatibility layers
- Testing at each checkpoint

**When to Read**: Planning or executing Phase 2 migration

---

## Phase 3 Documents (To Be Created)

### Optional Features

#### Entity Registry Integration
**Status**: 📝 To be created
**Lines**: ~300 (estimated)
**Focus**: ER patterns, area assignment, UI integration

**Key Topics**:
- Entity registry API usage
- Area selection in config flow
- Entity metadata updates
- Service for metadata management

**When to Read**: If implementing area/entity management features

---

#### Diagnostic Sensors
**Status**: 📝 To be created
**Lines**: ~250 (estimated)
**Focus**: Observability sensors, quality metrics, update patterns

**Key Topics**:
- Reading count sensor
- Last reading timestamp sensor
- Data quality score calculation
- Efficient update mechanisms

**When to Read**: If implementing observability features

---

#### Repair Detection
**Status**: 📝 To be created
**Lines**: ~300 (estimated)
**Focus**: Issue detection, repair flows, proactive management

**Key Topics**:
- Orphaned statistics detection
- Data gap detection
- Repair flow implementation
- Issue registry integration

**When to Read**: If implementing proactive issue detection

---

#### Config Flow Enhancements
**Status**: 📝 To be created
**Lines**: ~200 (estimated)
**Focus**: Preview, validation, import existing

**Key Topics**:
- Preview step in config flow
- Unit selection with icons
- Import from existing statistics
- Validation in config flow

**When to Read**: If improving configuration UX

---

#### Panel Enhancements
**Status**: 📝 To be created
**Lines**: ~200 (estimated)
**Focus**: UI improvements, bulk operations, dashboards

**Key Topics**:
- Data quality dashboard
- Bulk operation UI
- Import/export improvements
- Statistics viewer

**When to Read**: If improving panel/UI features

---

#### Phase 3 Decision Guide
**Status**: 📝 To be created
**Lines**: ~250 (estimated)
**Focus**: Cost-benefit analysis, when to skip features, prioritization

**Key Topics**:
- Feature-by-feature cost-benefit
- Decision criteria
- When to skip Phase 3
- Feature prioritization matrix

**When to Read**: Deciding whether to implement Phase 3 features

---

## Quick Reference

### By Task Type

#### Implementing Validation
Read these files:
1. [Validation Patterns](phase-1/validation-patterns.md)
2. [Error Handling Patterns](phase-1/error-handling-patterns.md)
3. Service Organization Strategy (TBD)

#### Refactoring Services
Read these files:
1. Service Base Classes (TBD)
2. Service Module Structure (TBD)
3. Service Categorization (TBD)

#### Adding New Service
Read these files:
1. Service Base Classes (TBD)
2. Service Schema Management (TBD)
3. [Validation Patterns](phase-1/validation-patterns.md)

#### Planning Implementation
Read these files:
1. [Phase 1 Migration Guide](phase-1/migration-guide.md)
2. Phase 2 Migration Guide (TBD)
3. Phase 3 Decision Guide (TBD)

#### Troubleshooting Issues
Read these files:
1. [Error Handling Patterns](phase-1/error-handling-patterns.md)
2. [Validation Patterns](phase-1/validation-patterns.md)
3. Diagnostic Sensors (TBD)

---

## Implementation Status Tracking

### Phase 1 Status

| Task | Document | Status | Completion |
|------|----------|--------|------------|
| Validation patterns | [validation-patterns.md](phase-1/validation-patterns.md) | ✅ Doc Complete | 0% |
| Error handling | [error-handling-patterns.md](phase-1/error-handling-patterns.md) | ✅ Doc Complete | 0% |
| Migration guide | [phase-1-migration-guide.md](phase-1/phase-1-migration-guide.md) | ✅ Doc Complete | 0% |
| Service organization | TBD | 📝 To Extract | 0% |
| Type safety | TBD | 📝 To Extract | 0% |

### Phase 2 Status

| Task | Document | Status | Completion |
|------|----------|--------|------------|
| Base classes | TBD | 📝 To Create | 0% |
| Categorization | TBD | 📝 To Create | 0% |
| Schema management | TBD | 📝 To Create | 0% |
| Module structure | TBD | 📝 To Create | 0% |
| Migration guide | TBD | 📝 To Create | 0% |

### Phase 3 Status

| Task | Document | Status | Completion |
|------|----------|--------|------------|
| Entity registry | TBD | 📝 To Create | 0% |
| Diagnostic sensors | TBD | 📝 To Create | 0% |
| Repair detection | TBD | 📝 To Create | 0% |
| Config flow | TBD | 📝 To Create | 0% |
| Panel enhancements | TBD | 📝 To Create | 0% |
| Decision guide | TBD | 📝 To Create | 0% |

---

## Document Creation Roadmap

### Immediate (Current Session)
- ✅ Phase 1: Validation Patterns
- ✅ Phase 1: Error Handling Patterns
- ✅ Phase 1: Migration Guide
- 🔄 This Index

### Next Priority
- 📝 Phase 1: Service Organization Strategy (extract)
- 📝 Phase 1: Type Safety Standards (extract)
- 📝 Phase 2: All core documents (extract)

### Future
- 📝 Phase 3: All optional feature documents (extract)
- 📝 Cross-reference updates
- 📝 Examples and diagrams

---

## Cross-Reference Map

### Validation Patterns References
- → Error Handling Patterns (exception usage)
- → Service Organization Strategy (where validation applies)
- → Phase 1 Migration Guide (implementation timeline)

### Error Handling Patterns References
- → Validation Patterns (validators that trigger exceptions)
- → Service Organization Strategy (where error handling applies)
- → Phase 1 Migration Guide (testing strategy)

### Migration Guide References
- → Validation Patterns (what's being implemented)
- → Error Handling Patterns (what's being implemented)
- → Service Organization Strategy (structure context)

---

## File Size Guidelines

Following handbook philosophy:

| Size Range | Status | Action |
|------------|--------|--------|
| < 100 lines | ❌ Too small | Consider merging with related content |
| 100-500 lines | ✅ Optimal | Perfect size for focused reading |
| 500-700 lines | ⚠️ Large | Consider splitting if multiple topics |
| > 700 lines | ❌ Too large | Must split into focused files |

---

## Original Phase Files

The original monolithic PRD files are kept for reference:

- `phase-1-core-improvements.md` (~1200 lines) - ⚠️ Too large
- `phase-2-service-architecture.md` (~1000 lines) - ⚠️ Too large
- `phase-3-optional-features.md` (~900 lines) - ⚠️ Too large

**Status**: To be deprecated once all focused files are created

---

## Success Metrics

### Documentation Quality
- ✅ All files 100-500 lines (optimal range)
- ✅ Each file covers ONE focused topic
- ✅ Clear cross-references between related files
- ✅ Independent readability

### LLM Efficiency
- ✅ Can read 2-3 files without token overflow
- ✅ Parallel reading possible
- ✅ Quick navigation (<5 minutes to find relevant guidance)

### Implementation Support
- ✅ Clear autonomy levels per task
- ✅ Explicit tool hints
- ✅ Concrete examples
- ✅ Testing strategies included

---

## Maintenance

### Updating Documents

When making changes:
1. Update specific focused file (not entire phase)
2. Check cross-references still valid
3. Update this index if files added/removed
4. Update status tracking table

### Adding New Documents

When adding new PRD:
1. Ensure 100-500 line range
2. Add to appropriate phase directory
3. Update this index with entry
4. Add cross-references
5. Update status tracking

---

## Related Documents

- **[LLM Operator's Handbook](../llm-operators-handbook.md)**: Operational guidance for implementing these PRDs
- **[ADR-000](../decision-records/000-llm-first-operations-model)**: The operational model guiding this structure

---

## Questions & Support

### For Implementation Questions
Read the specific focused file for your task, then check cross-referenced documents.

### For Structural Questions
Refer to LLM Operator's Handbook for operational patterns.

### For Escalation
Follow escalation procedures in the handbook.
