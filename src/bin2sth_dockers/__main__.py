import functools
import os
import pathlib
import platform
import subprocess
from typing import Tuple, Union

import fire

ENABLE_PROXY = (os.getenv('ENABLE_PROXY') or '').lower() not in \
               ('', '0', 'false', 'off', 'no', 'none')


def docker_root() -> pathlib.Path:
    path = pathlib.Path(__file__)

    while path:
        if (path / 'pyproject.toml').exists():
            return path / 'docker'
        path = path.parent

    raise RuntimeError('Cannot find folder dockers.')


def target_os(targets: Union[str, Tuple[str, ...]]):
    if not isinstance(targets, tuple):
        targets = (targets,)

    targets = tuple(target.lower() for target in targets)

    def wrapped(fn: callable):
        current_os = platform.system().lower()
        if current_os not in targets:
            @functools.wraps(fn)
            def disable_fn(*_args, **_kwargs):
                raise RuntimeError(f'This command shall be run on {targets}, '
                                   f'instead of current {current_os}.')

            disable_fn.__doc__ = \
                fn.__doc__ + f' Note: this command shall be run on {targets}'
            return disable_fn

        return fn

    return wrapped


class Docker:
    class Command:
        def __init__(self, command):
            self.args = ['docker', command]

        def run(self):
            print('$', ' '.join(str(arg) for arg in self.args))
            subprocess.run(args=self.args)

    class Build(Command):
        def __init__(self):
            super().__init__('build')

        def dockerfile(self, path: Union[str, os.PathLike]):
            self.args.extend(['-f', path])
            return self

        def tag(self, tag: str):
            self.args.extend(['-t', tag])
            return self

        def build_arg(self, key: str, val: str):
            self.args.extend(['--build-arg', f'{key}={val}'])
            return self

        def enable_proxy_if_required(self):
            if ENABLE_PROXY:
                self.build_arg('http_proxy', 'http://172.17.0.1:7890')
                self.build_arg('https_proxy', 'http://172.17.0.1:7890')
            return self

        def context(self, cwd: Union[str, os.PathLike] = '.'):
            self.args.append(cwd)
            return self

    class Pull(Command):
        def __init__(self):
            super().__init__('pull')

        def tag(self, tag: str):
            self.args.append(tag)
            return self


class BuildHelper:
    """
    Provide many build scripts for building valid docker images in a more
    reliable way.
    """

    @staticmethod
    @target_os('linux')
    def bap(opam_tag: str, bap_version: str):
        """
        Build bap image.

        :param opam_tag: Opam tag, such as ubuntu-21.04, debian, etc.
        :param bap_version: Bap version, only in 2.4.0~2.5.0
        """
        Docker.Pull() \
            .tag(f'ocaml/opam:{opam_tag}') \
            .run()

        Docker.Build() \
            .dockerfile(docker_root() / 'cmds' / 'bap' / 'Dockerfile') \
            .tag(f'bap/{opam_tag}:{bap_version}') \
            .build_arg('OPAM_TAG', opam_tag) \
            .build_arg('BAP_VERSION', bap_version) \
            .enable_proxy_if_required() \
            .context('.') \
            .run()

    @staticmethod
    @target_os('windows')
    def ida(ida_dir: str, ida_version: str, windows_tag: str = '20H2'):
        """
        Build ida image.

        :param ida_dir: Path to an ida installation directory. Note, this path
          should be relative because docker COPY requires that.
        :param ida_version: Version of ida.
        :param windows_tag: Tag of windows mage.
        """
        Docker.Build() \
            .dockerfile(docker_root() / 'cmds' / 'ida' / 'Dockerfile') \
            .tag(f'ida/win-{windows_tag.lower()}:{ida_version}') \
            .build_arg('IDA_DIR', ida_dir) \
            .build_arg('WINDOWS_TAG', windows_tag) \
            .enable_proxy_if_required() \
            .context('.') \
            .run()

    @staticmethod
    @target_os('windows')
    def rust_windows(rust_version: str, vs_version: str,
                     windows_tag: str = '20H2'):
        """
        Build rust on windows.

        :param rust_version: Version of rust, such as 1.65, etc.
        :param vs_version: Version of vs, such as 16 (vs2019), etc.
        :param windows_tag: Tag of windows image.
        """
        Docker.Pull() \
            .tag(f'mcr.microsoft.com/windows:{windows_tag}') \
            .run()

        Docker.Build() \
            .dockerfile(docker_root() / 'rust' / 'Dockerfile.windows.msvc') \
            .tag(f'rust/windows-msvc:vs-{vs_version}-rust-{rust_version}') \
            .build_arg('RUST_VERSION', rust_version) \
            .build_arg('VS_VERSION', vs_version) \
            .build_arg('WINDOWS_TAG', windows_tag) \
            .enable_proxy_if_required() \
            .context('.') \
            .run()

    class Cmdproxy:
        @staticmethod
        @target_os('linux')
        def bap(opam_tag: str, bap_version: str, cmdproxy_tag: str):
            """
            Build bap image is embedded with cmdproxy server.

            :param opam_tag: Opam tag, such as ubuntu-21.04, debian, etc.
            :param bap_version: Bap version, only in 2.4.0~2.5.0.
            :param cmdproxy_tag: Cmdproxy.rs tag.
            """
            Docker.Build() \
                .dockerfile(docker_root() / 'cmds' / 'bap'
                            / 'Dockerfile.cmdproxy') \
                .tag(f'cmdproxy/bap/{opam_tag}:'
                     f'cmdproxy-{cmdproxy_tag}-bap-{bap_version}') \
                .build_arg('OPAM_TAG', opam_tag) \
                .build_arg('BAP_VERSION', bap_version) \
                .build_arg('CMDPROXY_TAG', cmdproxy_tag) \
                .enable_proxy_if_required() \
                .context('.') \
                .run()

        @staticmethod
        @target_os('windows')
        def ida(ida_version: str, cmdproxy_tag: str, windows_tag: str = '20H2'):
            """
            Build ida image that is embedded with cmdproxy server.

            :param ida_version: Version of ida.
            :param cmdproxy_tag: Tag of cmdproxy image.
            :param windows_tag: Tag of windows image.
            """
            Docker.Build() \
                .dockerfile(docker_root() / 'cmds' / 'ida'
                            / 'Dockerfile.cmdproxy') \
                .tag(f'cmdproxy/ida/win-{windows_tag.lower()}:'
                     f'cmdproxy-{cmdproxy_tag}-ida-{ida_version}') \
                .build_arg('WINDOWS_TAG', windows_tag.lower()) \
                .build_arg('CMDPROXY_TAG', cmdproxy_tag) \
                .build_arg('IDA_TAG', ida_version) \
                .enable_proxy_if_required() \
                .context('.') \
                .run()


if __name__ == '__main__':
    fire.Fire({
        'build': BuildHelper
    })
