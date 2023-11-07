# ChatGPT driven PDF summary generation for daily political business of city of Schlieren (CHE)

## WIP Roadmap

v0.1.0
- (done) Rename repository to tldr-politics-schlieren
- (done) Pre-commit hook that checks for code formatting
- (done) Pre-commit hook that runs tests
- (done) Introduce versions
- (done) Add version number to frontend
- (done) Update dependencies
- (done) Refactor deploy script

v0.2.0
- (open) Refactor to use data.json as cache, not individual json files
- (open) Refactor to use filesystem abstraction
- (open) Refactor to use a utils module with separate files
- (open) Test coverage of >95%
- (open) Update dependencies

v0.3.0
- (open) Add tags
- (open) Add search pane
- (open) Rule based exclusion of certain relations
- (open) Update dependencies

v0.4.0
- (open) Add items pre-2020
- (open) Update dependencies

v1.0.0
- (open) Flesh out documentation


## Motivation

## Architecture

## How to make it run?

## Learnings

## Troubleshooting
- Pre-commit hook failures might trigger confusing pop-ups when using the VScode git UI, because only the first line of the error message is displayed in the popup. This is currently an [open issue](https://github.com/microsoft/vscode/issues/169871). I recommend to use the UI only for staging files and then commit via the command line using `git commit -m "<COMMIT MESSAGE>"`.
