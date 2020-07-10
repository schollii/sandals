"""
Provides some helper functions for helm. 

(C) Oliver Schoenborn
License: modified MIT, ie MIT plus the following restriction: This code 
can be included in your code base only as the complete file, and this 
license comment cannot be removed or changed. This code was taken from 
https://github.com/schollii/sandals/blob/master/json_sem_hash.py. 
GIT_COMMIT: EDIT WHEN COPY

If you find modifications necessary, please contribute a PR so that the 
open-source community can benefit the same way you benefit from this file.
"""

import hashlib
import json
import shutil
from pathlib import Path
from subprocess import run, PIPE
from tempfile import TemporaryDirectory
from typing import Union, List, Tuple

import pyaml

from json_sem_hash import get_json_sem_hash, JsonTree


def get_proc_out(cmd: Union[str, List[str]]) -> str:
    """
    Run the given command through subprocess.run() and return the
    output as a string.
    """
    shell = type(cmd) is str
    proc = run(cmd, shell=shell, stdout=PIPE)
    return proc.stdout.decode('UTF-8').strip()


def get_helm_install_merged_values_hash(
        service_name: str, namespace: str, *xtra_helm_args,
        values_files: List[str] = None, sets: List[str] = None,
        chart_dir_path: str = None) -> Tuple[str, JsonTree]:
    """
    Get a hash represents the merged values from a helm install command for a
    given service name, values files, sets, addition helm args, into a
    specific namespace. The chart path should be the relative or absolute
    path to the folder containing the Chart.yaml. The namespace is needed
    because we don't know whether a dry-run (used to compute the hash) uses it.

    Returns a pair: the first item is the hash value, the second is a dict
    representing the
    """
    dry_run_cmd = [
        'helm',
        'upgrade',
        '--install',
        '--namespace',
        namespace,
        service_name,
        chart_dir_path,
        '--dry-run',
        '--output',
        'json',
    ]
    if values_files:
        for vf in values_files:
            dry_run_cmd.append('-f')
            dry_run_cmd.append(vf)

    if sets:
        for s in sets:
            dry_run_cmd.append('--set')
            dry_run_cmd.append(s)

    dry_run_cmd.extend(xtra_helm_args)
    merged_values = json.loads(get_proc_out(dry_run_cmd))['config']
    config_hash = get_json_sem_hash(merged_values, hasher=hashlib.md5)

    return config_hash, merged_values


def create_versioned_chart(
        service_name: str, build_tag: str, namespace: str, *xtra_helm_args,
        values_files: List[str] = None, sets: List[str] = None,
        chart_dir_path: str = None, chart_prefix: str = '') -> Tuple[str, str, str]:
    """
    Create a versioned chart at given path, for the given service, build tag, values 
    files, and sets, for later installation in given namespace. The chart path is 
    path to the folder containing the Chart.yaml. By default, this is 
    chart/{chart_prefix}{service_name}. 
    
    The return value is a triplet, identifying the packaged chart's full name,
    (which will start with chart prefix), chart version string (contained in
    full name), and the full hash of the values used for (prior or to be done)
    installation.
    """
    if not chart_dir_path:
        chart_dir_path = f'chart/{chart_prefix}{service_name}'

    values_hash, merged_values = get_helm_install_merged_values_hash(
        service_name, namespace, *xtra_helm_args,
        chart_dir_path=chart_dir_path, values_files=values_files, sets=sets)
    # installation tag is the md5 hash (split into 4 dot-separated segments, for readability)
    # seg_len = 8
    # num_segs = int(len(config_hash)/seg_len)
    # install_tag = '.'.join(config_hash[seg_len * i: seg_len * i + seg_len] for i in range(num_segs))
    # installation tag is first N chars of the md5 hash
    keep_len = 12
    install_tag = values_hash[:keep_len]
    chart_version = f'{build_tag}-{install_tag}'
    print('Chart version:', chart_version)
    # print('App "version":', install_tag)

    with TemporaryDirectory(prefix='chart-', suffix=f'-{chart_version}') as tmpdirname:
        print(f'Created tmp chart folder {tmpdirname}')
        tmp_chart_path = Path(tmpdirname, Path(chart_dir_path).name)
        shutil.copytree(chart_dir_path, tmp_chart_path)
        # run(f'ls -R {tmpdirname}', shell=True)
        tmp_values_path = Path(tmp_chart_path, 'values.yaml')
        tmp_values_path.write_text(pyaml.dump(merged_values))
        # print(tmp_values_path.read_text(), '\n')

        package_cmd = f'helm package {tmp_chart_path} --version {chart_version}'
        run(package_cmd, shell=True)

    chart_fullname = f'{chart_prefix}{service_name}-{chart_version}.tgz'
    assert Path(chart_fullname).exists()
    return chart_fullname, chart_version, values_hash


def install_chart(
        service_name: str, build_tag: str, namespace: str, *xtra_helm_args,
        values_files: List[str] = None, sets: List[str] = None,
        chart_dir_path: str = None, chart_prefix: str = '') -> Tuple[str, str, str]:
    """
    Install a helm chart (via helm upgrade --install). This uses a somewhat unusual
    convention for the chart version and app version: there is no app version, and
    instead the chart version is the build tag + an md5 hash that represents the
    merged values (all values files, all sets, and the default values file of the
    chart). Moreover, the chart is repackaged to contain the merged values instead
    of the original default values file.

    The final chart is therefore completely standalone: it contains all the merged
    values, and the Chart.yaml has the chart version computed. It can be installed
    repeatedly without any values files. It can also be used as basis for other
    installations that also use this method.

    This function returns the triplet returned by create_versioned_chart(). 
    """
    chart_fullname, chart_version, values_hash = create_versioned_chart(
        service_name, build_tag, namespace, *xtra_helm_args,
        values_files=values_files, sets=sets,
        chart_dir_path=chart_dir_path, chart_prefix=chart_prefix)
    install_cmd = [
                      'helm',
                      'upgrade',
                      '--install',
                      '--namespace',
                      namespace,
                      service_name,
                      chart_fullname,
                  ] + list(xtra_helm_args)
    print(' '.join(install_cmd))
    run(install_cmd)
    return chart_fullname, chart_version, values_hash
