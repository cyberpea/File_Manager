import shutil
import psutil


def get_disks():
    """Собирает информацию о дисках устройства"""
    disks = []
    for part in psutil.disk_partitions():
        if "dontbrowse" in part.opts.split(","):
            continue
        try:
            usage = shutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        disks.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
        })
    return disks