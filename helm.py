"""
Provides some helper functions for helm. In particular, creation and installation
of a chart where app version is derived from a hash of the final set of values used 
for installation (all values files, all sets, and the default values file of the chart).

Requirements:
- Python 3.5+
- json_sem_hash.py (same repo)
- PyYAML

(C) Oliver Schoenborn
License: modified MIT, ie MIT plus the following restriction: This code 
can be included in your code base only as the complete file, and this 
license comment cannot be removed or changed. This code was taken from 
https://github.com/schollii/sandals/blob/master/helm.py.
GIT_COMMIT: <REPLACE WHEN FILE COPIED FROM GITHUB>

If you find modifications necessary, please contribute a PR so that the 
open-source community can benefit the same way you benefit from this file.
"""

import hashlib
import json
import math
import shutil
from pathlib import Path
from subprocess import run, PIPE
from tempfile import TemporaryDirectory
from typing import Union, List, Tuple

import yaml

from json_sem_hash import get_json_sem_hash, JsonTree


def _get_install_cmd(
    release_name: str, namespace: str, chart_dir_path: str, with_secrets: bool,
    values_files: List[str], sets: List[str], xtra_helm_args: Tuple[str],
    dry_run: bool = False
) -> List[str]:
    dry_run_cmd = [
        'helm',
        'upgrade',
        '--install',
        '--namespace',
        namespace,
        release_name,
        chart_dir_path,
    ]

    if dry_run:
        dry_run_cmd.extend([
            '--dry-run',
            '--output',
            'json',
        ])

    if with_secrets:
        dry_run_cmd.insert(1, 'secrets')

    if values_files:
        for vf in values_files:
            dry_run_cmd.append('-f')
            dry_run_cmd.append(vf)
    if sets:
        for s in sets:
            dry_run_cmd.append('--set')
            dry_run_cmd.append(s)

    dry_run_cmd.extend(xtra_helm_args)
    return dry_run_cmd


def get_proc_out(cmd: Union[str, List[str]]) -> str:
    """
    Run the given command through subprocess.run() and return the
    output as a string.
    """
    shell = type(cmd) is str
    proc = run(cmd, shell=shell, stdout=PIPE)
    return proc.stdout.decode('UTF-8').strip()


def get_helm_install_merged_values_hash(
        service_name: str, namespace: str, *xtra_helm_args: str,
        values_files: List[str] = None, sets: List[str] = None,
        chart_dir_path: str = None, with_secrets: bool = True) -> Tuple[str, JsonTree]:
    """
    Get a hash represents the merged values from a helm install command for a
    given service name, values files, sets, addition helm args, into a
    specific namespace. The chart path should be the relative or absolute
    path to the folder containing the Chart.yaml. The namespace is needed
    because we don't know whether a dry-run (used to compute the hash) uses it.

    Returns a pair: the first item is the hash value, the second is a dict
    representing the
    """
    dry_run_cmd = _get_install_cmd(
        service_name, namespace, chart_dir_path, with_secrets, values_files, sets,
        xtra_helm_args, dry_run=True)
    merged_values = json.loads(get_proc_out(dry_run_cmd))['config']
    config_hash = get_json_sem_hash(merged_values, hasher=hashlib.md5)

    return config_hash, merged_values


def format_hash(hash_str: str, hash_len: int, hash_seg_len: int, hash_sep: str) -> str:
    """
    Format a hash string: keep only hash_len chars from it, and break it up into
    segments of len hash_seg_len, using the hash_sep as separator. Ex:
    >>> format_hash('abcdef1232567890', 8, 2, '-')
    ab-cd-ef-12
    """
    hash_str = hash_str[:hash_len]
    if hash_seg_len >= hash_len:
        return hash_str
    num_segs = math.ceil(len(hash_str) / hash_seg_len)
    return hash_sep.join(hash_str[hash_seg_len * i: (hash_seg_len * i + hash_seg_len)]
                         for i in range(num_segs))


def install_hashed_chart(
    service_name: str, build_tag: str, namespace: str, *xtra_helm_args,
    release_name: str = None, with_secrets: bool = None,
    values_files: List[str] = None, sets: List[str] = None,
    chart_dir_path: str = None, chart_prefix: str = '',
    hash_len: int = 12, hash_seg_len: int = 4, hash_sep: str = '.',
):
    """
    Create a hashed chart from given path, for the given service, build tag, values
    files, and sets, assumed for installation in given namespace. The chart path is
    path to the folder containing the Chart.yaml. By default, this is 
    chart/{chart_prefix}{service_name}. The release_name will default to the
    service name unless specified.

    The return value is a triplet, identifying the packaged chart's full name,
    (which will start with chart prefix), chart version string (contained in
    full name), and the full hash of the values used for (prior or to be done)
    installation.
    """
    if not chart_dir_path:
        chart_dir_path = f'chart/{chart_prefix}{service_name}'
        print('Chart dir path:', chart_dir_path)
    if not release_name:
        release_name = service_name
        print('Release name:', release_name)
    if with_secrets is None:
        # default is: if we have it, use it!
        with_secrets = (run('helm secrets 2>1 > /dev/null', shell=True).returncode == 0)
        print('Use secrets:', with_secrets)

    values_hash, merged_values = get_helm_install_merged_values_hash(
        service_name, namespace, *xtra_helm_args, with_secrets=with_secrets,
        chart_dir_path=chart_dir_path, values_files=values_files, sets=sets)
    install_tag = format_hash(values_hash, hash_len, hash_seg_len, hash_sep)
    # chart_version = f'{build_tag}-{install_tag}'
    # print('Chart version:', chart_version)
    print('Chart version:', build_tag)
    print('App "version":', install_tag)

    with TemporaryDirectory(prefix='chart-', suffix=f'-{build_tag}-{install_tag}') as tmpdirname:
        print(f'Installing from tmp chart folder {tmpdirname}')
        tmp_chart_path = Path(tmpdirname, Path(chart_dir_path).name)
        shutil.copytree(chart_dir_path, tmp_chart_path)
        # run(f'ls -R {tmpdirname}', shell=True)
        chart_yaml_path = Path(tmp_chart_path, 'Chart.yaml')
        chart_info = yaml.safe_load(chart_yaml_path.read_text())
        chart_info['version'] = build_tag
        chart_info['appVersion'] = install_tag
        chart_yaml_path.write_text(yaml.dump(chart_info, default_flow_style=False))

        install_cmd = _get_install_cmd(
            release_name, namespace, str(tmp_chart_path), with_secrets, values_files, sets,
            xtra_helm_args)
        print(' '.join(install_cmd))
        run(install_cmd)
