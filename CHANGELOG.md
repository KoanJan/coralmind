# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
