# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-11-24

### Changed

- Require Python >= 3.11; drop Python 3.10 support.
- Follow the sibling package renames: `pyssp_sysml2` is now `pyssp_sysml`.

### Fixed

- The 0.2.0 wheel still reported `__version__` 0.1.0. The release tag guard now
  imports `pyssp_vv.__version__` instead of reading `pyproject.toml`, so a
  mismatch fails the build instead of shipping a lie.

## [0.2.0] - 2026-11-09

### Changed

- Fold the `measure` extra into the base dependencies.
- Harden the ecosystem CI workflows and seed the `CHANGELOG.md`.

