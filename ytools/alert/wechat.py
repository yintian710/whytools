# -*- coding: utf-8 -*-
"""
@File    : wechat.py
@Author  : yintian
@Date    : 2026/1/8 15:00
@Software: PyCharm
@Desc    : 
"""
from typing import Literal

from ytools import logger
from ytools.utils.magic import require

msg_type_literal = Literal["text", "markdown", "image", "news", "file", "voice", "template_card", ""]


async def async_send_wechat(content: str, to: list, at: list = None, msg_type: msg_type_literal = "text", **kwargs):
    """发送企业微信告警消息

    Args:
        content: 消息内容（text类型为纯文本，markdown类型为markdown格式）
        to: 机器人webhook URL列表或key列表
        at: at 列表
        msg_type: 消息类型，支持 "text" 和 "markdown"，默认为 "text"
    """

    require("httpx", action="fix")
    import httpx  # noqa
    for webhook in to:
        # 如果to是key，需要拼接完整URL，否则直接使用
        if not webhook.startswith("http"):
            # 这里假设webhook是完整URL，如果是key需要根据实际情况拼接
            webhook_url = webhook
        else:
            webhook_url = webhook

        # 根据消息类型构建payload
        payload = {
            "msgtype": msg_type,
            msg_type: {
                "content": content,
                "mentioned_list": at or [],
                **kwargs
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"[企业微信]发送成功！-> {content[:50]}...")
                else:
                    logger.error(f"[企业微信]发送失败！错误码：{result.get('errcode')}，错误信息：{result.get('errmsg')}")
        except Exception as e:
            logger.error(f"[企业微信]发送失败！原因：{e}")


def send_wechat(content: str, to: list, at: list = None, msg_type: msg_type_literal = "text", **kwargs):
    """发送企业微信告警消息

    Args:
        content: 消息内容（text类型为纯文本，markdown类型为markdown格式）
        to: 机器人webhook URL列表或key列表
        at: at 列表
        msg_type: 消息类型，支持 "text" 和 "markdown"，默认为 "text"
    """

    require("request", action="fix")
    import requests  # noqa
    payload = {
        "msgtype": msg_type,
        msg_type: {
            "content": content,
            "mentioned_list": at or [],
            **kwargs
        }
    }
    for webhook in to:
        # 如果to是key，需要拼接完整URL，否则直接使用
        if not webhook.startswith("http"):
            # 这里假设webhook是完整URL，如果是key需要根据实际情况拼接
            webhook_url = webhook
        else:
            webhook_url = webhook

        # 根据消息类型构建payload

        try:
            with requests.Session() as client:
                response = client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"[企业微信]发送成功！-> {content[:50]}...")
                else:
                    logger.error(f"[企业微信]发送失败！错误码：{result.get('errcode')}，错误信息：{result.get('errmsg')}")
        except Exception as e:
            logger.error(f"[企业微信]发送失败！原因：{e}")


if __name__ == '__main__':
    pass
