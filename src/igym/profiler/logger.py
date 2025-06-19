"""
import logging

class Logger:
    _instance
    '''
    单例模式
    '''

我能够在任何一个地方，调用Looger().log(tag, level, message) 
tag: "agent", "env"?

LoggerConfig? 保存到哪里？跨进程？因为env agent可能是两个不同的进程？
不同的文件夹？
- 用户没给文件夹，那就uuid？
- 给了就看看有没有重复？recover?读取已有的？
- 有重复，但是不是recover，那就新开一个，uuid


"""
