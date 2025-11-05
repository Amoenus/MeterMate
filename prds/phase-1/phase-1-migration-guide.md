# Phase 1 Migration Guide

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Validation Patterns](validation-patterns.md), [Error Handling Patterns](error-handling-patterns.md), [Service Organization Strategy](service-organization-strategy.md)
> **📅 Last Updated**: 2025-11-05

---

## Overview

This guide provides the complete implementation timeline, testing strategy, and success criteria for Phase 1: Core Improvements & Validation Patterns.

**Goal**: Systematically implement Phase 1 improvements with zero breaking changes and comprehensive validation.

**Autonomy Level**: 🟡 Collaborative - Implement autonomously with human validation at each task completion

---

## Phase 1 Summary

Phase 1 focuses on adopting **modern validation patterns** and **error handling best practices** without changing MeterMate's core functionality.

### What We're Improving
1. ✅ Enhanced schema validation with Voluptuous
2. ✅ Custom validators for MeterMate-specific validation
3. ✅ Comprehensive exception hierarchy
4. ✅ Standardized error handling across services
5. ✅ Improved type safety and documentation

### What We're NOT Changing
- ❌ Statistics table management approach
- ❌ Database access patterns
- ❌ Core data models
- ❌ Existing service functionality
- ❌ Any user-facing behavior (except better error messages)

---

## Implementation Timeline

**Total Duration**: 1-2 weeks
**Autonomy**: Implement each task, report completion for validation

### Week 1: Validation & Error Handling

#### Day 1-2: Custom Validators
**Task**: Create comprehensive validator library

**Steps**:
1. Create `custom_components/metermate/validators.py`
2. Implement all custom validators:
   - `metermate_entity_id`
   - `past_datetime`
   - `positive_float`
   - `valid_consumption`
   - `valid_meter_reading`
   - `valid_unit`
   - `timezone_aware_datetime`
3. Add comprehensive docstrings
4. Write unit tests for each validator

**Deliverables**:
- [ ] `validators.py` created with all validators
- [ ] Unit tests in `tests/test_validators.py`
- [ ] All tests passing

**Validation Checkpoint**: Review validator implementations and test coverage

#### Day 3: Exception Hierarchy
**Task**: Create custom exception classes

**Steps**:
1. Create `custom_components/metermate/exceptions.py`
2. Implement exception hierarchy:
   - `MeterMateError` (base)
   - `MeterMateValidationError`
   - `MeterMateEntityNotFoundError`
   - `MeterMateReadingNotFoundError`
   - `MeterMateDatabaseError`
   - `MeterMateInvalidStateError`
   - `MeterMateConfigError`
3. Add comprehensive docstrings
4. Write tests for exception hierarchy

**Deliverables**:
- [ ] `exceptions.py` created
- [ ] Unit tests in `tests/test_exceptions.py`
- [ ] All tests passing

**Validation Checkpoint**: Review exception hierarchy and usage patterns

#### Day 4: Enhanced Service Schemas
**Task**: Update all service schemas with new validators

**Steps**:
1. Update `services.yaml` (if needed for documentation)
2. Update each service schema in `services.py`:
   - `SERVICE_ADD_READING_SCHEMA`
   - `SERVICE_UPDATE_READING_SCHEMA`
   - `SERVICE_DELETE_READING_SCHEMA`
   - `SERVICE_ADD_METER_READING_SCHEMA`
   - `SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA`
   - `SERVICE_GET_READINGS_SCHEMA`
   - `SERVICE_BULK_IMPORT_SCHEMA`
   - `SERVICE_RECALCULATE_STATISTICS_SCHEMA`
   - `SERVICE_REBUILD_HISTORY_SCHEMA`
   - `SERVICE_IMPORT_FROM_CSV_SCHEMA`
3. Test each schema with valid and invalid input

**Deliverables**:
- [ ] All service schemas updated
- [ ] Schema tests in `tests/test_service_schemas.py`
- [ ] All tests passing

**Validation Checkpoint**: Review schema changes, ensure backward compatibility

#### Day 5: Service Error Handling
**Task**: Implement error handling pattern in all services

**Steps**:
1. Update each service handler to use new exceptions:
   - Add entity existence checks
   - Add business logic validation
   - Add proper exception handling
   - Add comprehensive logging
2. Update service handler signatures/docstrings
3. Test error paths for each service

**Deliverables**:
- [ ] All service handlers updated with error handling
- [ ] Error handling tests in `tests/test_service_errors.py`
- [ ] All tests passing

**Validation Checkpoint**: Review error handling, test error messages

### Week 2: Polish & Testing

#### Day 6: Type Safety & Documentation
**Task**: Add type hints and comprehensive documentation

**Steps**:
1. Add type hints to all functions
2. Create TypedDict definitions for service data
3. Update all docstrings to Google style
4. Add module-level documentation
5. Run mypy type checking

**Deliverables**:
- [ ] All functions have type hints
- [ ] TypedDict definitions created
- [ ] All docstrings updated
- [ ] mypy passes with no errors

**Validation Checkpoint**: Review type annotations and documentation

#### Day 7: Integration Testing
**Task**: Comprehensive integration testing

**Steps**:
1. Test all services with real data
2. Test error paths end-to-end
3. Test validation with edge cases
4. Test backward compatibility
5. Performance testing (ensure no regression)

**Deliverables**:
- [ ] Integration test suite complete
- [ ] All tests passing
- [ ] Performance benchmarks show no regression

**Validation Checkpoint**: Review test results and performance

#### Day 8: Documentation & Examples
**Task**: Update user-facing documentation

**Steps**:
1. Update README with validation changes
2. Add examples of new error messages
3. Document migration path for users
4. Update changelog
5. Create validation guide for users

**Deliverables**:
- [ ] README updated
- [ ] CHANGELOG.md updated
- [ ] Validation guide created
- [ ] Examples added

**Validation Checkpoint**: Review documentation clarity

#### Day 9-10: Buffer & Refinement
**Task**: Address any issues, refinement, and final validation

**Steps**:
1. Address feedback from previous checkpoints
2. Refactor any unclear code
3. Add any missing tests
4. Final integration testing
5. Prepare for Phase 2

**Deliverables**:
- [ ] All feedback addressed
- [ ] Code quality high
- [ ] All tests passing
- [ ] Ready for deployment

**Final Validation**: Complete Phase 1 review before Phase 2

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 95%+ for new code

#### Validator Tests
```python
# tests/test_validators.py
def test_past_datetime_accepts_past()
def test_past_datetime_rejects_future()
def test_positive_float_accepts_positive()
def test_positive_float_rejects_negative()
def test_valid_consumption_accepts_reasonable()
def test_valid_consumption_rejects_large()
def test_metermate_entity_id_accepts_sensor()
def test_metermate_entity_id_rejects_non_sensor()
# ... etc for all validators
```

#### Exception Tests
```python
# tests/test_exceptions.py
def test_exception_hierarchy()
def test_exception_can_catch_base()
def test_exception_messages()
def test_exception_context_preserved()
```

#### Schema Tests
```python
# tests/test_service_schemas.py
async def test_add_reading_schema_valid()
async def test_add_reading_schema_negative_value()
async def test_add_reading_schema_invalid_unit()
async def test_add_reading_schema_future_timestamp()
# ... etc for all schemas and validation rules
```

### Integration Tests

**Coverage Target**: All service operations and error paths

```python
# tests/test_service_integration.py
async def test_add_reading_success()
async def test_add_reading_entity_not_found()
async def test_add_reading_duplicate_timestamp()
async def test_add_reading_invalid_value()
async def test_delete_reading_not_found()
async def test_bulk_import_partial_success()
# ... etc
```

### Manual Testing Checklist

After automated tests pass, manually verify:

- [ ] Submit valid reading via UI - success message
- [ ] Submit negative value - clear error message
- [ ] Submit future timestamp - clear error message
- [ ] Submit invalid unit - clear error message
- [ ] Try to add duplicate timestamp - helpful error
- [ ] Try to update non-existent reading - helpful error
- [ ] Try to delete non-existent reading - helpful error
- [ ] Bulk import with some errors - partial success reported
- [ ] Check logs show appropriate levels (INFO, WARNING, ERROR)
- [ ] Existing automations still work

---

## Migration Path

### Phase 1A: Add Infrastructure (Non-Breaking)

**Week 1, Days 1-3**

1. Create `validators.py` with all validators
2. Create `exceptions.py` with exception hierarchy
3. Add comprehensive tests

**Status**: ✅ Non-breaking - just adding new modules

### Phase 1B: Update Schemas (Non-Breaking)

**Week 1, Day 4**

1. Update service schemas to use new validators
2. Keep existing behavior (warnings only initially)
3. Test with real-world data

**Status**: ✅ Non-breaking - existing calls still work, just better validation

### Phase 1C: Implement Error Handling (Non-Breaking)

**Week 1, Day 5**

1. Update service handlers with new exception types
2. Add comprehensive error handling
3. Improve error messages

**Status**: ✅ Non-breaking - better error messages, same functionality

### Phase 1D: Enable Strict Validation (Potentially Breaking)

**Week 2, Days 6-7**

1. Switch from warnings to errors for invalid input
2. Update documentation with new requirements
3. Announce in changelog

**Status**: ⚠️ Potentially breaking - clearly communicate in release notes

---

## Success Criteria

### Must Have ✅

**Code Quality**:
- [ ] All custom validators implemented
- [ ] Complete exception hierarchy
- [ ] All service schemas updated
- [ ] Error handling standardized across services
- [ ] Type hints on all functions
- [ ] Comprehensive docstrings

**Testing**:
- [ ] Unit test coverage >95% for new code
- [ ] All validators tested
- [ ] All exception types tested
- [ ] All schema validation rules tested
- [ ] Integration tests for all services
- [ ] Error path testing complete

**Compatibility**:
- [ ] 100% backward compatibility maintained
- [ ] No breaking changes to existing integrations
- [ ] Existing automations work unchanged
- [ ] No performance regression

**Documentation**:
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] Migration guide created
- [ ] Examples documented

### Should Have 🎯

- [ ] Validation guide for users
- [ ] Error message catalog
- [ ] Troubleshooting guide
- [ ] Performance benchmarks documented

### Nice to Have ✨

- [ ] Validation bypass flag for advanced users
- [ ] Validation severity configuration
- [ ] Error metrics/monitoring

---

## Validation Checkpoints

### Checkpoint 1: After Day 2
**Review**: Validator implementations and tests
**Human Validates**:
- All validators work correctly
- Test coverage is comprehensive
- Error messages are clear

### Checkpoint 2: After Day 3
**Review**: Exception hierarchy
**Human Validates**:
- Exception types are appropriate
- Hierarchy makes sense
- Usage examples are clear

### Checkpoint 3: After Day 4
**Review**: Schema updates
**Human Validates**:
- Schemas are complete
- Backward compatibility maintained
- Validation is appropriate

### Checkpoint 4: After Day 5
**Review**: Error handling implementation
**Human Validates**:
- Error handling is consistent
- Error messages are helpful
- Logging is appropriate

### Checkpoint 5: After Day 7
**Review**: Integration testing results
**Human Validates**:
- All tests pass
- No performance regression
- Manual testing successful

### Final Checkpoint: End of Week 2
**Review**: Complete Phase 1 implementation
**Human Validates**:
- All success criteria met
- Documentation complete
- Ready for deployment
- Ready to start Phase 2

---

## Rollback Plan

If issues are discovered during implementation:

### Minor Issues
- Fix and continue
- Update tests
- Document in commit message

### Major Issues
If validation breaks existing functionality:

1. **Immediate**: Revert problematic changes
2. **Analyze**: Identify root cause
3. **Fix**: Implement proper solution
4. **Test**: Comprehensive testing
5. **Redeploy**: With fixes

### Emergency Rollback
If deployment breaks production:

1. Revert to previous version
2. Document issue
3. Escalate to human for decision
4. Plan fix implementation

---

## Performance Benchmarks

### Baseline Measurements
Before Phase 1, measure:
- Service call latency (avg, p95, p99)
- Memory usage
- Database query count per operation

### Target Performance
After Phase 1:
- Service latency: <5% increase acceptable
- Memory usage: <10% increase acceptable
- Query count: No increase

### Monitoring
Track during implementation:
- Run performance tests after each task
- Compare to baseline
- Flag any regression >5%

---

## Risk Management

### Risk: Breaking Existing Automations
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Comprehensive backward compatibility testing
- Gradual rollout with warnings first
- Clear changelog and migration guide
**Escalation**: If any breaking change detected

### Risk: Performance Degradation
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Performance testing at each checkpoint
- Benchmark comparisons
- Optimize if regression detected
**Escalation**: If degradation >5%

### Risk: Over-Strict Validation
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Start with warnings before errors
- Collect feedback from users
- Allow bypass for advanced users
**Escalation**: If users report valid use cases blocked

---

## Tool Usage Patterns

### For This Phase

**Most Used**:
- `replace_string_in_file` - Updating service schemas and handlers
- `create_file` - Creating validators and exceptions files
- `runTests` - Validating changes
- `read_file` - Understanding existing code

**Occasionally Used**:
- `semantic_search` - Finding all service registration points
- `grep_search` - Locating all schema definitions
- `list_code_usages` - Finding validator usage
- `get_errors` - Checking for type errors

---

## Communication Templates

### Task Completion Report

```markdown
## Task Completed: [Task Name]

**Duration**: [X hours/days]
**Status**: ✅ Complete

### Deliverables
- [x] Deliverable 1
- [x] Deliverable 2

### Tests
- Unit tests: [X] passing
- Integration tests: [X] passing
- Coverage: [X]%

### Issues Encountered
[None | Description of issues and how resolved]

### Ready for Validation
[Summary of what to review]
```

### Checkpoint Review Request

```markdown
## Checkpoint [N]: [Checkpoint Name]

**Completed Tasks**:
- Task 1
- Task 2

**Test Results**:
- All [X] tests passing
- Coverage: [X]%
- Performance: [within targets | describe variance]

**Review Requested**:
1. [Specific aspect 1]
2. [Specific aspect 2]

**Next Steps** (pending approval):
- [Next task]
```

---

## Related Documents

- **[Validation Patterns](validation-patterns.md)**: Details of validators being implemented
- **[Error Handling Patterns](error-handling-patterns.md)**: Exception hierarchy and error handling
- **[Service Organization Strategy](service-organization-strategy.md)**: Context for where validation fits

---

## References

- Home Assistant Testing: https://developers.home-assistant.io/docs/development_testing
- Python Testing Best Practices: https://docs.pytest.org/en/stable/
- Type Checking with mypy: https://mypy.readthedocs.io/
