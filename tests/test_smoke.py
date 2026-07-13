"""Smoke tests: the package imports and exposes the domain constant."""


def test_package_imports():
    import custom_components.openwindows as pkg

    assert pkg is not None


def test_domain_constant():
    from custom_components.openwindows import const

    assert const.DOMAIN == "openwindows"
