# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.11] - 2026-03-17

### Added

- **TaskStep Model**: Encapsulated execution parameters into a unified `TaskStep` class
  - Consolidates `materials`, `requirements`, `output_constraints`, `language`, `relevant_requirements` into single object
  - Cleaner method signatures for `Executor.execute()` and `Validator.validate_execution()`
  - Better parameter management and code organization

- **Plan Deliverable Field**: Added `deliverable` field to `Plan` class
  - Describes the final deliverable of the plan (e.g., "a piece of code")
  - Provides clear context for what the plan aims to produce

- **ContentSpec-Deliverable Consistency**: Validation ensures final node's `content_spec` matches plan's `deliverable`
  - Prompt-level constraint for LLM to maintain consistency
  - Ensures semantic alignment between plan goal and final output

- **Code Documentation**: Added comprehensive English comments to `_orchestrate` method
  - Clear documentation of execution flow
  - Explains each step: initialization, node execution, validation loop, intermediate data storage

### Changed

- **Material Passing Strategy**: All materials are now passed to every node by default
  - Simplified execution model: no need for LLM to decide material relevance per node
  - More robust execution with full context available at each step

### Removed

- **Material Coverage Validation**: Removed the check that all materials must be used in plan
  - Simplified validation logic
  - Aligns with new material passing strategy where all materials are available to all nodes

## [0.0.10] - 2026-03-16

### Changed

- **OutputConstraints Refactoring**: Separated format and semantic validation
  - `output_type`: TEXT or MODEL (renamed from STR/DICT for better semantics)
  - `fields`: Field definitions for MODEL type (format validation)
  - `content_spec`: Content specification for semantic validation (now required)

- **Strong Typing with Dynamic BaseModel**: Replaced `dict[str, str]` with dynamically generated BaseModel
  - Added `OutputConstraints.get_model_class()` method for dynamic model creation
  - Better type safety and validation throughout the codebase
  - Removed all dict-related functions (`_to_dict`, `_fix_dict_structure_by_llm`)

- **Required Fields**: Made `output_constraints` and `content_spec` mandatory
  - Every node must have explicit output constraints
  - Every node must have content specification for semantic validation

- **Prompt Updates**: Updated `PLAN_STANDARD` prompt to use new `output_constraints` structure
  - Clear guidance for LLM to use MODEL type for intermediate nodes
  - TEXT type for final nodes
  - Includes `content_spec` for semantic validation

### Removed

- **Dict Support**: Removed all `dict[str, str]` support from `call_llm`
  - Simplified type system to `str | BaseModel`
  - Removed `FIX_DICT_STRUCTURE` template and related functions

## [0.0.9] - 2026-03-15

### Added

- **Intelligent Requirements Matching**: Structured requirement tree with semantic search
  - Automatic requirement tree construction for large requirements (>1000 chars)
  - Vector similarity matching to provide only relevant requirement sections to each node
  - Significant token cost reduction for complex tasks
  - Persistent caching of requirement trees by task template

- **Robustness Features for Requirement Tree**:
  - Auto-repair: Automatically adds "Other" fallback node when LLM misses requirement segments
  - Smart warnings: Only logs warnings when missing ratio exceeds 5% threshold
  - Graceful degradation: Returns "Other" node content when semantic search finds no matches

### Changed

- **Requirements Splitting**: Simplified to newline-based splitting (was sentence-based)
  - Preserves semantic integrity of each line
  - Respects user's original document structure

- **Agent Configuration**: Added `embedding_llm` parameter for semantic search capability
  - Optional: Falls back to full requirements mode when not configured
  - Lazy initialization: Only builds tree when first needed

## [0.0.8] - 2026-03-14

### Added

- **Global Requirements Context**: Propagate original requirements to each execution step
  - Added `global_requirements` parameter to Executor and Validator
  - Added `GLOBAL_REQUIREMENTS_CONTEXT` prompt template (CN/EN)
  - Helps maintain alignment with overall task goals throughout multi-step execution

- **Material Coverage Validation**: Ensure all materials are used in plan
  - Integrated into `_validate_plan_structure` method
  - Raises `PlanValidationError` if any material is not referenced in plan

- **Plan Generation Retry**: Simple retry mechanism for plan validation failures
  - Added `max_retry_times_for_plan` parameter to Agent (default: 3)

### Changed

- **Scoring System Redesign**: Replaced multi-dimensional scoring with dependency-based rating
  - New sequential evaluation: deliverable type → logic → requirements completion → depth/innovation
  - Clearer grading criteria: Failed(0-2) → Poor(3-4) → Average(5-6) → Good(7-8) → Excellent(9-10)

- **Method Renaming**: `Validator.validate` renamed to `validate_execution` for clarity

## [0.0.7] - 2026-03-12

### Fixed

- **Executor Material Format**: Added material name header in executor messages for better LLM context
  - Before: Material content was passed without context
  - After: Material content is formatted with name header (`# {name}\n\n{content}\n`)

## [0.0.6] - 2026-03-11

### Added

- **Multi-language Prompt System**: Full internationalization support for prompts
  - Added `Language` enum (EN, CN) as public API in model package
  - Created language-specific prompt directories (`en/`, `cn/`)
  - All prompts now support both English and Chinese

### Changed

- **Prompt Architecture Refactoring**: Complete restructure for better maintainability
  - `name.py`: `PromptName` and `PromptTemplateName` enums for type-safe prompt access
  - `static.py`: Static prompts (PLAN_STANDARD, EVALUATION_STANDARD)
  - `template.py`: Template prompts requiring formatting
  - `func.py`: Complex build functions (build_score_messages, build_validation_messages)
  - Removed old `llm.py`, `worker.py`, `evaluation_standard.py`, `plan_standard.py` from prompts

- **Type Safety**: Replaced string-based prompt names with enums
  - `PromptName` for static prompts (used with `get_prompt()`)
  - `PromptTemplateName` for template prompts (used with `build_prompt()`)

- **Dependency Decoupling**: `Language` enum moved from prompts to model package
  - `model.Language` is now the public API
  - `prompts` package uses internal `_get_module_prefix()` for language dispatch

## [0.0.5] - 2026-03-09

### Fixed

- **Planner Prompt Design**: Fixed issue where LLM incorrectly referenced "Final Output Format" as a material
  - Moved output_format to a separate section outside Task Input
  - Added explicit warnings that output_format is NOT a material
  - Added "Materials (Available for input_fields)" label for clarity

### Changed

- **Debug Logging**: Added comprehensive debug logging for main workflow key nodes
  - Agent: task execution, template extraction, plan generation, node execution, orchestration, evaluation
  - Worker: plan generation, validation, execution details
  - OutputFormat: JSON Schema to Pydantic model conversion

## [0.0.4] - 2026-03-08

### Added

- **JSON Schema Support**: New `output_format` module with comprehensive JSON Schema to Pydantic model conversion
  - `json_schema_to_pydantic()` function for dynamic model generation
  - Support for `$defs` and `$ref` references
  - Support for `enum` and `const` types
  - Support for `anyOf`, `oneOf`, `allOf` combination types
  - Support for `null` type and nullable fields
  - Support for string constraints: `minLength`, `maxLength`, `pattern`, `format`
  - Support for numeric constraints: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
  - Support for array constraints: `minItems`, `maxItems`
  - Support for `additionalProperties` control
  - Support for nested objects and arrays

### Changed

- **Breaking**: Renamed `OutputFormater` to `OutputFormatter` (corrected spelling)
- **Breaking**: Renamed `output_formater` attribute to `output_formatter` in `Agent` class
- Improved code style and linting compliance across all modules
- Fixed variable naming: `meterials_names` → `materials_names`, `node_indicies` → `node_indices`

### Fixed

- Documentation typos in README.md and README_CN.md

## [0.0.3] - 2026-03-07

### Added

- Token cost tracking throughout the execution pipeline
- Evaluation flow refactoring for better scoring mechanism

## [0.0.2] - 2026-03-04

### Fixed

- CI/CD pipeline issues

## [0.0.1] - 2026-03-04

### Added

- Initial release with core features:
  - Self-evolving AI Agent framework
  - Intelligent planning with multi-node execution
  - Result validation with rule-based and semantic checks
  - Closed-loop feedback with LLM scoring
  - Persistent storage for task templates and plans
  - ThresholdStrategy for plan reuse optimization
