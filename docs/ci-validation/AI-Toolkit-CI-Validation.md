# Temporary CI validation branch

This marker file exists only to create a pull-request-triggered run of the repository's existing quality-gates workflow against the current `latest/development` tree, including the AI Toolkit and its exhaustive Playwright suite.

It is not intended to be merged into `latest/development` and should be removed by closing the validation pull request after the test status is reviewed.

The file was updated after opening the draft to ensure the existing pull-request workflow receives a synchronize event.
