"""Assemble a local-only Windows researcher kit. Never upload or publish it."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from psyml import __version__

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-zip', type=Path, required=True)
    args = parser.parse_args()
    version = __version__
    sources = json.loads((ROOT / 'output/pdf/sources.json').read_text())
    for name, expected in sources.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f'PDF source changed; regenerate PDFs: {name}')
    destination = ROOT / f'PsyML-Toolkit-Researcher-Share-v{version}'
    if destination.exists():
        raise SystemExit(f'Remove or relocate the existing kit before rebuilding: {destination}')
    with zipfile.ZipFile(args.windows_zip) as archive:
        names = archive.namelist()
        prefix = f'PsyML-Toolkit-{version}-Windows-x64/'
        metadata = json.loads(archive.read(prefix + 'BUILD.json'))
        assert metadata['version'] == version and not metadata['working_tree_modified']
        assert archive.read(prefix + 'SMOKE_TEST.txt') == b'PSYML_NATIVE_BUNDLE_OK'
        assert prefix + 'PsyML Toolkit.exe' in names
        for name in names:
            relative = Path(name.removeprefix(prefix))
            if not name.startswith(prefix) or relative.is_absolute() or '..' in relative.parts:
                raise SystemExit(f'Unexpected archive path: {name}')
        for name in names:
            if name.endswith('/'):
                continue
            target = destination / 'Windows' / name.removeprefix(prefix)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    shutil.copytree(ROOT / 'examples/quickstart', destination / 'TestData')
    documents = destination / 'Documents'
    documents.mkdir()
    for source, target in [('README_ZH.pdf', '中文使用指南.pdf'),
                           ('RESEARCHER_GUIDE_ZH.pdf', '中文术语解释.pdf')]:
        shutil.copy2(ROOT / 'output/pdf' / source, documents / target)
    start = f'''PsyML Toolkit v{version} - 研究者分享包（Windows x64）

从这里开始
1. 请先将整个压缩包完整解压到本机文件夹，不要在压缩包中直接运行。
2. 打开 Windows 文件夹，双击 PsyML Toolkit.exe。保留 core 和其他文件。
   已含运行环境，无需安装 Python、Godot 或输入命令。
3. 在第 1 页“导入配置…”选择 TestData/classification_config.json。
   训练 CSV 自动加载；保持“保存最佳模型”勾选（随机种子下方）。
4. 第 2 页选择结果保存位置并运行；第 3 页查看结果并打开完整结果文件夹。
5. 第 4 页确认模型来源可信，加载结果 model/best_decision_tree.joblib。
   保留旁边的 model_metadata.json，再加载 TestData/classification_predict.csv。
   运行预测，应得到 10 行；点击“预测结果另存为…”保存。
6. 回归测试使用 regression_config.json、best_ridge.joblib 和 regression_predict.csv。

文件夹说明
Windows/：Windows 64 位独立程序、内置运行环境、许可证及应用附带样例。
TestData/：集中测试资料；*_config.json 是配置，*_train.csv 是训练数据，
          *_predict.csv 是新预测数据。请保留配置与对应训练数据在同一目录。
          README.md 逐项解释文件用途。这里与 Windows/examples/quickstart 内容相同。
Documents/中文使用指南.pdf：中文版 README、分享包快速开始和界面操作图解。
Documents/中文术语解释.pdf：模型、验证、指标、结果、参数与新数据预测术语。
SHARE_MANIFEST.json：本包文件校验信息，通常无需打开。

Mac 用户
本分享包只含 Windows 版。Apple 芯片 Mac 请到 GitHub 下载 macOS-arm64 ZIP：
https://github.com/GuGuGu-coocoo/PsyMl_Toolkit/releases/tag/v{version}
完整解压后打开 PsyML Toolkit.app。GitHub 的 Source code 是源码，不是应用。

所有测试数据均为合成数据，只用于熟悉软件。预测流程通过不代表真实研究效果。
仅加载自己训练或来源可信的模型。首次启动若系统询问，请核对来源并按系统提示处理。
本分享压缩包仅供直接分享，不作为 GitHub Release 附件上传。
'''
    (destination / '从这里开始.txt').write_text(start, encoding='utf-8-sig')
    inventory = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination / 'SHARE_MANIFEST.json').write_text(json.dumps({
        'version': version, 'distribution': 'local-only; do not upload to release',
        'windows_build_commit': metadata['commit'], 'files': inventory,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    result = shutil.make_archive(str(destination), 'zip', destination.parent, destination.name)
    archive_path = Path(result)
    archive_path.with_suffix('.zip.sha256').write_text(
        hashlib.sha256(archive_path.read_bytes()).hexdigest() + '  ' + archive_path.name + '\n')
    print(result)


if __name__ == '__main__':
    main()
