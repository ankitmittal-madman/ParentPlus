"""Approved disposable database container selection."""

import os


def get_test_container():
    name = os.environ.get(
        "PARENTPLUS_TEST_CONTAINER",
        "parentplus-pg-test",
    )

    if name not in {
        "parentplus-pg-test",
        "parentplus-pg-ci-fresh",
    }:
        raise RuntimeError(
            "STOP: Unapproved database test container"
        )

    return name
