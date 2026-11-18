"""docker-compose.yml, .env.example and the .env generator agree with each other (US-20)."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
IMAGES_WORKFLOW = (ROOT / ".github" / "workflows" / "images.yml").read_text(
    encoding="utf-8"
)
DEPENDABOT = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
DOCKERFILES = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("apps", "services", "policies")
    for path in (ROOT / folder).rglob("Dockerfile")
)
EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
SETTINGS = re.findall(r"^([A-Z][A-Z0-9_]*)=", EXAMPLE, flags=re.MULTILINE)

spec = importlib.util.spec_from_file_location(
    "make_env", ROOT / "tools" / "dev" / "make_env.py"
)
make_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_env)


def test_compose_uses_every_setting_in_the_example_and_no_other():
    used = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", COMPOSE))

    assert used == set(SETTINGS)


def test_the_example_values_are_placeholders_that_no_service_accepts():
    values = re.findall(r"^[A-Z][A-Z0-9_]*=(.*)$", EXAMPLE, flags=re.MULTILINE)

    assert set(values) == {"replace-me"}


def test_the_generator_fills_every_setting_with_a_long_random_value(tmp_path):
    output = tmp_path / ".env"

    assert make_env.main(["--output", str(output)]) == 0

    written = dict(
        line.split("=", 1)
        for line in output.read_text(encoding="utf-8").splitlines()
        if re.match(r"^[A-Z]", line)
    )
    assert list(written) == SETTINGS
    assert all(len(value) >= 32 for value in written.values())
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in written.values())
    assert len(set(written.values())) == len(written)


def test_the_generator_never_overwrites_an_existing_file(tmp_path, capsys):
    output = tmp_path / ".env"
    output.write_text("KEEP=me\n", encoding="utf-8")

    assert make_env.main(["--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "KEEP=me\n"
    assert "--force" in capsys.readouterr().err
    assert make_env.main(["--output", str(output), "--force"]) == 0


def test_every_dockerfile_is_built_scanned_and_watched():
    assert len(DOCKERFILES) == 5
    for dockerfile in DOCKERFILES:
        assert f"dockerfile: {dockerfile}" in IMAGES_WORKFLOW, dockerfile
        assert f"dockerfile: {dockerfile}" in COMPOSE, dockerfile
        assert f'"/{dockerfile.rsplit("/", 1)[0]}"' in DEPENDABOT, dockerfile


def test_every_service_image_is_built_from_this_repository_except_postgres():
    pulled = re.findall(
        r"^    image: (?!agentsentinel/)(\S+)$", COMPOSE, flags=re.MULTILINE
    )

    assert [image.split(":")[0] for image in pulled] == ["pgvector/pgvector"]
