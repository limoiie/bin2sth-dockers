import functools
import os
import pathlib
import platform
import subprocess
from typing import Tuple, Union

import fire

DOCKER_REGISTRY = os.getenv("DOCKER_REGISTRY")
ENABLE_PROXY = os.getenv("ENABLE_PROXY")


def docker_root(*parts) -> pathlib.Path:
    path = pathlib.Path(__file__)

    while path:
        if (path / "pyproject.toml").exists():
            return path.joinpath("docker", *parts)
        path = path.parent

    raise RuntimeError("Cannot find folder dockers.")


def target_os(targets: Union[str, Tuple[str, ...]]):
    """
    Annotator that will panic if the host does not match the targets.

    :param targets: The legal host conditions.
    :return: The wrapped function.
    """
    if not isinstance(targets, tuple):
        targets = (targets,)

    targets = tuple(target.lower() for target in targets)

    def wrapped(fn: callable):
        current_os = platform.system().lower()
        if current_os not in targets:

            @functools.wraps(fn)
            def disable_fn(*_args, **_kwargs):
                raise RuntimeError(
                    f"This command shall be run on {targets}, "
                    f"instead of current {current_os}."
                )

            disable_fn.__doc__ = (
                fn.__doc__ + f" Note: this command shall be run on {targets}"
            )
            return disable_fn

        return fn

    return wrapped


def push_to_registry(fn=None):
    """
    Annotator that push the tag to registry defined by env var DOCKER_REGISTRY.

    :param fn: The function that will return a tag going to be pushed.
    :return: The wrapped function.
    """
    if fn is None:
        return push_to_registry

    @functools.wraps(fn)
    def push_to_registry_after_fn(*args, **kwargs):
        tag = fn(*args, **kwargs)
        if DOCKER_REGISTRY:
            remote_tag = DOCKER_REGISTRY + "/" + tag
            Docker.Tag().copy(tag, remote_tag).run()
        return tag

    return push_to_registry_after_fn


class Docker:
    class Command:
        def __init__(self, command):
            self.args = ["docker", command]

        def run(self):
            print("$", " ".join(str(arg) for arg in self.args))
            subprocess.run(args=self.args)

    class Build(Command):
        def __init__(self):
            super().__init__("build")

        def dockerfile(self, path: Union[str, os.PathLike]):
            self.args.extend(["-f", path])
            return self

        def tag(self, tag: str):
            self.args.extend(["-t", tag])
            return self

        def build_arg(self, key: str, val: str):
            self.args.extend(["--build-arg", f"{key}={val}"])
            return self

        def enable_proxy_if_required(self):
            if (ENABLE_PROXY or "").lower() not in ("", "off", "false", "0"):
                if not ENABLE_PROXY.startswith("http") and not ENABLE_PROXY.startswith(
                    "socket"
                ):
                    proxy = "http://172.17.0.1:7890"
                else:
                    proxy = ENABLE_PROXY

                self.build_arg("http_proxy", proxy)
                self.build_arg("https_proxy", proxy)
            return self

        def context(self, cwd: Union[str, os.PathLike] = "."):
            self.args.append(cwd)
            return self

    class Pull(Command):
        def __init__(self):
            super().__init__("pull")

        def tag(self, tag: str):
            self.args.append(tag)
            return self

    class Tag(Command):
        def __init__(self):
            super().__init__("tag")

        def copy(self, tag, new_tag):
            self.args.extend((tag, new_tag))
            return self


class BuildHelper:
    """
    Provide many build scripts for building valid docker images in a more
    reliable way.
    """

    @staticmethod
    @target_os("linux")
    @push_to_registry
    def vcpkg(ubuntu_tag: str, vcpkg_tag: str):
        """
        Build vcpkg image.

        :param ubuntu_tag: Ubuntu tag, such as 18.04, 22.04, etc.
        :param vcpkg_tag: Name of branch, tag, or commit of repo vcpkg.
        """
        Docker.Pull().tag(f"ubuntu:{ubuntu_tag}").run()

        tag = f"vcpkg/ubuntu-{ubuntu_tag}:{vcpkg_tag}"
        root = docker_root() / "cmds" / "vcpkg"
        (
            Docker.Build()
            .dockerfile(root / "Dockerfile")
            .tag(tag)
            .build_arg("UBUNTU_TAG", ubuntu_tag)
            .build_arg("VCPKG_TAG", vcpkg_tag)
            .enable_proxy_if_required()
            .context(root)
            .run()
        )
        return tag

    @staticmethod
    @target_os("linux")
    @push_to_registry
    def bap(opam_tag: str, bap_version: str):
        """
        Build bap image.

        :param opam_tag: Opam tag, such as ubuntu-21.04, debian, etc.
        :param bap_version: Bap version, only in 2.4.0~2.5.0
        """
        (Docker.Pull().tag(f"ocaml/opam:{opam_tag}").run())

        tag = f"bap/{opam_tag}:{bap_version}"
        (
            Docker.Build()
            .dockerfile(docker_root("cmds", "bap", "Dockerfile"))
            .tag(tag)
            .build_arg("OPAM_TAG", opam_tag)
            .build_arg("BAP_VERSION", bap_version)
            .enable_proxy_if_required()
            .context(".")
            .run()
        )
        return tag

    @staticmethod
    @target_os("windows")
    @push_to_registry
    def ida(ida_dir: str, ida_version: str, windows_tag: str = "20H2"):
        """
        Build ida image.

        :param ida_dir: Path to an ida installation directory. Note, this path
          should be relative because docker COPY requires that.
        :param ida_version: Version of ida.
        :param windows_tag: Tag of windows mage.
        """
        tag = f"ida/win-{windows_tag.lower()}:{ida_version}"
        (
            Docker.Build()
            .dockerfile(docker_root("cmds", "ida", "Dockerfile"))
            .tag(tag)
            .build_arg("IDA_DIR", ida_dir)
            .build_arg("WINDOWS_TAG", windows_tag)
            .enable_proxy_if_required()
            .context(".")
            .run()
        )
        return tag

    @staticmethod
    @target_os("windows")
    @push_to_registry
    def rust_windows(rust_version: str, vs_version: str, windows_tag: str = "20H2"):
        """
        Build rust on windows.

        :param rust_version: Version of rust, such as 1.65, etc.
        :param vs_version: Version of vs, such as 16 (vs2019), etc.
        :param windows_tag: Tag of windows image.
        """
        (Docker.Pull().tag(f"mcr.microsoft.com/windows:{windows_tag}").run())

        tag = f"rust/windows-msvc:vs-{vs_version}-rust-{rust_version}"
        (
            Docker.Build()
            .dockerfile(docker_root("rust", "Dockerfile.windows.msvc"))
            .tag(tag)
            .build_arg("RUST_VERSION", rust_version)
            .build_arg("VS_VERSION", vs_version)
            .build_arg("WINDOWS_TAG", windows_tag)
            .enable_proxy_if_required()
            .context(".")
            .run()
        )
        return tag

    class Cmdproxy:
        """
        Provide many helper scripts for building cmdproxy-server-version
        microservice images.
        """

        @staticmethod
        @target_os("linux")
        @push_to_registry
        def vcpkg(ubuntu_tag: str, vcpkg_tag: str, cmdproxy_tag: str):
            """
            Build vcpkg image.

            :param ubuntu_tag: Ubuntu tag, such as 18.04, 22.04, etc.
            :param vcpkg_tag: Name of branch, tag, or commit of repo vcpkg.
            :param cmdproxy_tag: Cmdproxy.rs tag.
            """
            tag = (
                f"cmdproxy/vcpkg/ubuntu-{ubuntu_tag}:"
                f"cmdproxy-{cmdproxy_tag}-vcpkg-{vcpkg_tag}"
            )
            root = docker_root() / "cmds" / "vcpkg"
            (
                Docker.Build()
                .dockerfile(root / "Dockerfile.cmdproxy")
                .tag(tag)
                .build_arg("UBUNTU_TAG", ubuntu_tag)
                .build_arg("VCPKG_TAG", vcpkg_tag)
                .build_arg("CMDPROXY_TAG", cmdproxy_tag)
                .enable_proxy_if_required()
                .context(root)
                .run()
            )
            return tag

        @staticmethod
        @target_os("linux")
        @push_to_registry
        def bap(opam_tag: str, bap_version: str, cmdproxy_tag: str):
            """
            Build bap image is embedded with cmdproxy server.

            :param opam_tag: Opam tag, such as ubuntu-21.04, debian, etc.
            :param bap_version: Bap version, only in 2.4.0~2.5.0.
            :param cmdproxy_tag: Cmdproxy.rs tag.
            """
            tag = (
                f"cmdproxy/bap/{opam_tag}:" f"cmdproxy-{cmdproxy_tag}-bap-{bap_version}"
            )
            (
                Docker.Build()
                .dockerfile(docker_root("cmds", "bap", "Dockerfile.cmdproxy"))
                .tag(tag)
                .build_arg("OPAM_TAG", opam_tag)
                .build_arg("BAP_VERSION", bap_version)
                .build_arg("CMDPROXY_TAG", cmdproxy_tag)
                .enable_proxy_if_required()
                .context(".")
                .run()
            )
            return tag

        @staticmethod
        @target_os("windows")
        @push_to_registry
        def ida(ida_version: str, cmdproxy_tag: str, windows_tag: str = "20H2"):
            """
            Build ida image that is embedded with cmdproxy server.

            :param ida_version: Version of ida.
            :param cmdproxy_tag: Tag of cmdproxy image.
            :param windows_tag: Tag of windows image.
            """
            tag = (
                f"cmdproxy/ida/win-{windows_tag.lower()}:"
                f"cmdproxy-{cmdproxy_tag}-ida-{ida_version}"
            )
            (
                Docker.Build()
                .dockerfile(docker_root("cmds", "ida", "Dockerfile.cmdproxy"))
                .tag(tag)
                .build_arg("WINDOWS_TAG", windows_tag.lower())
                .build_arg("CMDPROXY_TAG", cmdproxy_tag)
                .build_arg("IDA_TAG", ida_version)
                .enable_proxy_if_required()
                .context(".")
                .run()
            )
            return tag


if __name__ == "__main__":
    fire.Fire({"build": BuildHelper})
