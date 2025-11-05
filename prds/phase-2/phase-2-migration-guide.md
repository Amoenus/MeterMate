# Phase 2 Migration Guide

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Service Base Classes](service-base-classes.md), [Service Module Structure](service-module-structure.md)
> **📅 Last Updated**: 2025-11-06

---

## Overview

This guide provides the complete implementation timeline, testing strategy, and success criteria for Phase 2: Service Architecture Enhancement.

**Goal**: Migrate from monolithic services.py to modular service architecture with zero breaking changes.

**Autonomy Level**: 🟡 Collaborative - Implement autonomously with human validation at each week milestone

---

## Phase 2 Summary

Phase 2 refactors MeterMate's service architecture from a single monolithic file to a modular, category-based structure while maintaining 100% backward compatibility.

### What We're Changing
1. ✅ Monolithic `services.py` → Modular `services/` directory
2. ✅ Single class → Base class hierarchy
3. ✅ Inline schemas → Centralized `schemas.py`
4. ✅ Mixed services → Categorized (query/mutation/admin)
5. ✅ Ad-hoc patterns → Consistent service structure

### What We're NOT Changing
- ❌ Service functionality or behavior
- ❌ Service names or schemas (unless improving validation)
- ❌ Integration with data_manager
- ❌ Any user-facing behavior

---

## Implementation Timeline

**Total Duration**: 2-3 weeks
**Autonomy**: Implement each week, report for validation at milestone

### Week 1: Infrastructure

#### Day 1-2: Base Classes & Schemas
**Task**: Create service base classes and centralized schemas

**Steps**:
1. Create `services/base.py` with all base classes
2. Create `services/schemas.py` with all schemas
3. Write comprehensive tests for base classes
4. Validate schema completeness

**Deliverables**:
- [ ] `services/base.py` complete
- [ ] `services/schemas.py` complete
- [ ] Base class tests passing
- [ ] Schema tests passing

**Validation Checkpoint**: Review base class design and schema organization

#### Day 3: Directory Structure & Registration
**Task**: Create directory structure and registration system

**Steps**:
1. Create `services/` directory structure
2. Create `services/__init__.py` with registration
3. Create category `__init__.py` files
4. Test registration system independently

**Deliverables**:
- [ ] Directory structure created
- [ ] Registration system working
- [ ] Category modules created
- [ ] Registration tests passing

**Validation Checkpoint**: Review directory structure and registration pattern

#### Day 4-5: Query Services Migration
**Task**: Migrate query services first (safest)

**Steps**:
1. Create `services/queries/get_readings.py`
2. Create `services/queries/validate_reading.py`
3. Update tests for migrated services
4. Verify services work with new structure

**Deliverables**:
- [ ] All query services migrated
- [ ] Tests updated and passing
- [ ] Services registered correctly
- [ ] Backward compatibility verified

**Validation Checkpoint**: Review query service migration

### Week 2: Service Migration

#### Day 6-8: Mutation Services Migration
**Task**: Migrate mutation services

**Steps**:
1. Migrate reading services (add/update/delete)
2. Migrate meter reading services
3. Migrate consumption period services
4. Update all tests

**Deliverables**:
- [ ] All mutation services migrated
- [ ] Tests updated and passing
- [ ] Error handling consistent
- [ ] Logging standardized

**Validation Checkpoint**: Review mutation service migration

#### Day 9-10: Admin Services Migration
**Task**: Migrate admin services

**Steps**:
1. Migrate bulk import service
2. Migrate rebuild history service
3. Migrate recalculate statistics service
4. Migrate CSV import service
5. Verify admin permissions work

**Deliverables**:
- [ ] All admin services migrated
- [ ] Admin permissions enforced
- [ ] Safety checks in place
- [ ] Prominent logging working

**Validation Checkpoint**: Review admin service migration and permissions

### Week 3: Polish & Testing

#### Day 11-12: Integration Testing
**Task**: Comprehensive end-to-end testing

**Steps**:
1. Test all services with real data
2. Test service discovery
3. Test registration/unregistration
4. Performance testing

**Deliverables**:
- [ ] Integration test suite complete
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] No regressions detected

**Validation Checkpoint**: Review test results

#### Day 13: Documentation
**Task**: Update all documentation

**Steps**:
1. Update README with new structure
2. Create service developer guide
3. Update CHANGELOG
4. Document migration for contributors

**Deliverables**:
- [ ] Documentation updated
- [ ] Examples added
- [ ] Migration guide complete
- [ ] CHANGELOG updated

**Validation Checkpoint**: Review documentation

#### Day 14-15: Cleanup & Deprecation
**Task**: Clean up old code, prepare for deployment

**Steps**:
1. Deprecate old `services.py` (keep as compatibility layer)
2. Add deprecation warnings if needed
3. Final testing
4. Prepare release notes

**Deliverables**:
- [ ] Old code deprecated properly
- [ ] All tests passing
- [ ] Release notes prepared
- [ ] Ready for deployment

**Final Validation**: Complete Phase 2 review

---

## Migration Strategy

### Three-Phase Approach

#### Phase 2A: Create New Structure (Week 1)
- Create new `services/` directory alongside old `services.py`
- Both systems coexist
- No breaking changes
- **Status**: ✅ Non-breaking

#### Phase 2B: Migrate Services (Week 2)
- Migrate services one category at a time
- Update `__init__.py` to use new services
- Old `services.py` becomes re-export for compatibility
- **Status**: ✅ Non-breaking

#### Phase 2C: Deprecate Old Code (Week 3)
- Mark old `services.py` as deprecated
- Update all internal references to new structure
- Keep old file for external compatibility
- **Status**: ✅ Non-breaking (deprecated but functional)

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 95%+ for new code

```python
# Test base classes
def test_abstract_base_cannot_instantiate()
def test_derived_must_implement_abstract()
def test_query_service_registers_with_response()
def test_mutation_service_logs_operations()
def test_admin_service_registers_as_admin()

# Test individual services
async def test_service_name_is_correct()
async def test_service_has_schema()
async def test_service_execution_success()
async def test_service_error_handling()
```

### Integration Tests

```python
async def test_all_services_registered()
async def test_service_discovery()
async def test_query_service_returns_data()
async def test_mutation_service_persists()
async def test_admin_service_requires_permissions()
async def test_backward_compatibility()
```

### Manual Testing Checklist

- [ ] All services callable from UI
- [ ] Query services return data
- [ ] Mutation services modify data
- [ ] Admin services require admin role
- [ ] Error messages clear
- [ ] Logging appropriate
- [ ] Performance acceptable
- [ ] Existing automations work

---

## Success Criteria

### Must Have ✅
- [ ] All services migrated to new structure
- [ ] Base class hierarchy implemented
- [ ] Schemas centralized
- [ ] 100% backward compatibility
- [ ] All tests passing
- [ ] No performance regression

### Should Have 🎯
- [ ] Service developer guide
- [ ] Clear categorization
- [ ] Consistent patterns
- [ ] Comprehensive tests
- [ ] Documentation complete

### Nice to Have ✨
- [ ] Service auto-discovery
- [ ] Service metadata
- [ ] Performance monitoring
- [ ] Migration tooling

---

## Validation Checkpoints

### Checkpoint 1: End of Week 1
**Review**: Base infrastructure
**Human Validates**:
- Base class design sound
- Schema organization clear
- Registration system works

### Checkpoint 2: Day 10
**Review**: Service migration progress
**Human Validates**:
- All services migrated correctly
- Tests comprehensive
- Error handling consistent

### Checkpoint 3: End of Week 3
**Review**: Complete Phase 2
**Human Validates**:
- All success criteria met
- Documentation complete
- Ready for deployment

---

## Risk Management

### Risk: Breaking Existing Code
**Mitigation**:
- Keep old `services.py` as compatibility layer
- Extensive backward compatibility testing
- Gradual rollout

### Risk: Registration Issues
**Mitigation**:
- Test registration independently
- Verify all service types register correctly
- Check admin permissions work

### Risk: Performance Degradation
**Mitigation**:
- Benchmark before and after
- Profile service execution
- Optimize if needed

---

## Rollback Plan

### Minor Issues
- Fix and continue
- Update tests
- Document in commit

### Major Issues
If migration breaks functionality:
1. Revert to old `services.py`
2. Analyze root cause
3. Fix and re-test
4. Redeploy

---

## Related Documents

- **[Service Base Classes](service-base-classes.md)**: What we're building
- **[Service Categorization](service-categorization.md)**: How services are organized
- **[Service Module Structure](service-module-structure.md)**: Directory layout
- **[Service Schema Management](service-schema-management.md)**: Centralized schemas

---

## References

- Home Assistant service patterns: https://developers.home-assistant.io/docs/dev_101_services
- Python refactoring best practices: https://refactoring.guru/refactoring
- Migration strategies: https://martinfowler.com/articles/practical-test-pyramid.html
