# Markdown 语法速查词典 - 链接与媒体篇

> 目标：覆盖代码、链接、图片、HTML 和页内跳转。

## 代码

行内代码渲染效果：

使用 `printf()` 输出。

行内代码源码：

```markdown
使用 `printf()` 输出。
```

代码块渲染效果：

```c
#include <stdio.h>

int main(void) {
    printf("Hello, Markdown!\n");
    return 0;
}
```

代码块源码：

````markdown
```c
#include <stdio.h>

int main(void) {
    printf("Hello, Markdown!\n");
    return 0;
}
```
````

带语言标识的代码块渲染效果：

```python
def hello():
    print("hello")
```

带语言标识的代码块源码：

```markdown
```python
def hello():
    print("hello")
```
```

## 链接

普通链接渲染效果：

[OpenAI](https://openai.com)

普通链接源码：

```markdown
[OpenAI](https://openai.com)
```

带标题的链接渲染效果：

[OpenAI](https://openai.com "OpenAI 官网")

带标题的链接源码：

```markdown
[OpenAI](https://openai.com "OpenAI 官网")
```

引用式链接渲染效果：

这是一个[引用式链接][openai]。

引用式链接源码：

```markdown
这是一个[引用式链接][openai]。

[openai]: https://openai.com
```

自动链接渲染效果：

<https://openai.com>
<mail@example.com>

自动链接源码：

```markdown
<https://openai.com>
<mail@example.com>
```

## 图片

渲染效果：

![替代文本](https://example.com/image.png)

源码：

```markdown
![替代文本](https://example.com/image.png)
```

引用式图片渲染效果：

![替代文本][logo]

引用式图片源码：

```markdown
![替代文本][logo]

[logo]: https://example.com/image.png
```

## 行内 HTML

部分渲染器允许直接写 HTML。

渲染效果：

<span style="color:red;">红色文字</span>

<details>
  <summary>点击展开</summary>
  这里是隐藏内容。
</details>

源码：

```markdown
<span style="color:red;">红色文字</span>

<details>
  <summary>点击展开</summary>
  这里是隐藏内容。
</details>
```

## 锚点与目录

渲染效果：

[跳到表格](#表格)

源码：

```markdown
[跳到表格](#表格)
```

说明：

- 标题通常会自动生成锚点。
- 不同渲染器的锚点规则可能略有差异。

