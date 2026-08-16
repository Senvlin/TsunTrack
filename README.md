# TsunTrack

> 让 Python 的报错变得**傲娇**起来～


---
基于 [rich](https://github.com/Textualize/rich) 的全局异常美化器, 零侵入、纯配置驱动的全局异常美化器, 安装即用, 自带傲娇人格. 

## 效果

未安装 / 关闭时: 

<img width="907" height="211" alt="zzz" src="https://github.com/user-attachments/assets/7307dcf1-858f-4541-b502-b852a5badb9d" />

安装并启用后: 

<img width="918" height="271" alt="PixPin_2026-08-16_22-33-18" src="https://github.com/user-attachments/assets/ec4e79bb-bcb4-46aa-8b1f-e22fae36c514" />



## 特性

- **风格切换**: 报错不再是冷冰冰的堆栈, 改一句 `[general] theme = "..."`, 你可以自由改成毒舌、治愈、中二……任何风格
- **装完即用**: 通过 `tsuntrack_auto.pth` 在解释器启动时自动安装钩子, 业务代码零改动
- **配置文件驱动**: 报错文案、样式全部来自 TOML 配置, 可自定义颜色, 支持部分覆盖与扩展占位符
- **手动接口**: 也可以 `import tsuntrack; tsuntrack.install()` 手动启用
- **智能信息增强**: 保留并美化 Python 原生的 `did-you-mean` 提示
- **文本丰富化**: 堆栈自带语法高亮, 主题多样. 配置文件支持 `[green]`/`[red]` 等 Rich 标记
> 只想要报错美化？把theme字段改成空字符串就能体验了
## 安装

要求 Python 3.11+. 使用 pip: 

```powershell
pip install tsuntrack
```

安装后无需任何 import——随便跑一个会报错的脚本, 看看效果吧: 

```powershell
python -c "print(1/0)"
```

## 手动启用 / 关闭

```python
import tsuntrack

tsuntrack.install()      # 启用
tsuntrack.uninstall()    # 关闭, 恢复默认行为
```

## 配置

### 查找顺序(优先级从高到低)

1. 环境变量 `TSUNTRACK_CONFIG` 指定的路径
2. 当前工作目录下的 `tsuntrack.toml`
3. 用户主目录 `~/.config/tsuntrack/config.toml`
4. 包内置 `defaults.toml`

用户配置与默认配置**深合并**:, 只需写你想改的字段

### 示例

```toml
[general]
enabled = true # 总开关
theme = "tsuntere" # 当前主题
max_frames = 5 # 最多显示的堆栈层数(保留最内层)
context_lines = 1 # 上下文代码显示行数
error_line_style = "bold red" # 报错代码高亮颜色
line_number_style = "dim" # 行数颜色
show_hints = true # 是否显示提示
            
# 上下文代码高亮:

[general.syntax]
# - theme: pygments 内置主题名(如 monokai / default / emacs / friendly / tango),
theme = "monokai"

[general.syntax.styles] 
# - styles: pygments token 名 → rich 样式. token 名如 Keyword / Name.Function / String.Doc.
# 以下键值对的键值需要写Pygment自带的Token，自创的会默认不显示，
"Comment.Special" = "bold #5C6370"
"Comment" = "#5C6370"
"String.Doc" = "italic #5C6370"
"String" = "#98C379"
...

# 主题内为某个异常覆盖文案
[theme."tsuntere".exceptions.NameError]
template = '小笨蛋, 才, 才不会告诉你这个“{name}”没定义呢, 哼╯^╰'
```


### 主题

配置分三层合并, **优先级从高到低**: 

1. **用户配置**(`tsuntrack.toml` / 环境变量指定文件 / `~/.config/...`)——直接覆盖下面任何内容
2. **主题覆盖层**(`[theme."主题名".*]`)——按 `[general] theme` 选中的主题覆盖基础配置
3. **基础配置**(`defaults.toml` 中除 `[theme.*]` 外的部分)——所有主题共用, `exceptions.default` 兜底

```toml
# 1) 切换内置主题
[general]
theme = "傲娇"

# 2) 直接覆盖任意配置
[exceptions.NameError]
template = '我的自定义文案: {name}'

# 3) 自定义主题(在自己配置里加一段 [theme."名字"...] 即可)
[general]
theme = "我的主题"

[theme."我的主题".exceptions.NameError]
template = '我的主题文案: {name}'
```

### 占位符

| 占位符 | 含义 | 示例 |
| --- | --- | --- |
| `{name}` | 变量名 / 属性名 / 模块名 / 键名(NameError、AttributeError、ModuleNotFoundError、KeyError 等) | `some_undefined_name` |
| `{message}` | 异常自带的消息文本 | `division by zero` |
| `{exc_type}` | 异常类型名 | `NameError` |
| `{filename}` | 出错文件路径(最内层栈帧) | `C:\demo\app.py` |
| `{lineno}` | 出错行号 | `8` |
| `{func_name}` | 出错函数名 | `level_1` |
| `{module}` | 出错模块名 | `app` |

#### 自定义占位符(`[extra]`)

可在用户配置或主题中添加 `[extra]` 段，定义任意额外占位符：

```toml
# tsuntrack.toml(或环境变量指定的配置)
[extra]
service = "order-api"
env = "production"
```

```toml
[theme."neko".exceptions.default]
template = '主人, {service} 在 {env} 环境出错了: {message}, 人家会好好处理的!'
```

输出：`主人, order-api 在 production 环境出错了: ...`


- `[extra]` 的键与`[general]`中同名时覆盖内置字段
- 主题层同样生效：`[theme."X".extra]` 可按主题定义不同占位符
- 也可以从代码调用：`formatter.format_message(exc_type, exc_value, tb, cfg, extra={"service": "x"})`

### 关闭

```toml
[general]
enabled = false
```

放在任意优先级的配置文件中即可全局关闭(钩子不会被安装). 

## 已知限制

- 只接管主线程的未捕获异常(`sys.excepthook`)
  - 线程内未捕获异常与 `sys.unraisablehook` 暂未接管
  - `asyncio` 任务中的异常也不会触发
 > 若其他库也替换了 sys.excepthook，可能会静默覆盖
- `python -S`(不加载 site)等模式下 `.pth` 不会被执行, 需手动 `tsuntrack.install()`

## License

MIT
