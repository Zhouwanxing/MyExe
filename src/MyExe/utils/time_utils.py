from datetime import datetime


def current_datetime_str(fmt="%Y-%m-%d %H:%M:%S"):
    """
    获取当前时间的字符串，默认格式 'YYYY-MM-DD HH:MM:SS'

    Args:
        fmt (str): 时间格式化字符串，默认 "%Y-%m-%d %H:%M:%S"

    Returns:
        str: 格式化后的时间字符串
    """
    now = datetime.now()
    return now.strftime(fmt)


def current_date_str(fmt="%Y-%m-%d"):
    """
    获取当前日期字符串，默认格式 'YYYY-MM-DD'
    """
    now = datetime.now()
    return now.strftime(fmt)


def current_time_str(fmt="%H:%M:%S"):
    """
    获取当前时间字符串，默认格式 'HH:MM:SS'
    """
    now = datetime.now()
    return now.strftime(fmt)
