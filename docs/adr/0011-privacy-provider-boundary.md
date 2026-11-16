# 0011. 隐私边界与 provider 抽象

- 状态：已接受
- 日期：2026-11-14
- 关联：[0001](0001-closed-world-kb.md)、[0007](0007-deepseek-api-model-tiering.md)、[0012](0012-output-contract.md)

## 背景

待核验文章可能是未发布草稿，知识库可能是内部文档。DeepSeek API 的隐私政策允许用输入/输出训练和改进模型，未提供零数据保留（ZDR）选项；Responses API 声明不存储 response 状态，但这不等于不用于训练。另一方面，用户已确认 v1 的文章和 KB 以公开内容为主，需要快速落地。

## 决策

1. 默认允许云端 DeepSeek 调用；发送范围是**文章全文 + 检索到的 KB 片段**，不整库上传。
2. manifest 的 `sensitivity` 与配置中的 `sensitivity` 取更严格者：
   - `public`：默认允许。
   - `internal` / `confidential`：默认拒绝运行，必须显式 `--allow-confidential`。
3. 运行开始前打印一行数据边界提示（模型、发送范围、敏感级别）；不阻塞公开内容。
4. API Key 只从 `DEEPSEEK_API_KEY` 读取，永不写入 trace、报告或缓存；`.env` 加入 `.gitignore`。
5. 运行产物默认保存原文副本；`--no-store-article` 只保留哈希、主张和证据引用。
6. **provider 抽象**：v1 只实现 DeepSeek Responses API 适配器，但判定层依赖 `LLMProvider` 协议；v2 可接入本地模型或其他 API，而不改判定/闸门逻辑。
7. v1 不引入 LangChain；v2 若引入，仅用于编排，不改变闭世界与闸门约束。

## 备选方案

- **不加限制，直接发送**：把"可能用于训练"埋在默认行为里；排除。
- **全部本地模型**：隐私最好，但质量/硬件约束大，且与 v1 快速落地冲突；排除。
- **先拿 opt-out/企业协议再实现**：周期不可控；v1 不做，但保留 provider 切换路径。
- **对文章做脱敏**：会破坏逐字引用，进而破坏证据链；v1 不做。

## 后果

- 公开内容可以开箱即用；机密内容需要用户显式承担风险或等待本地 provider。
- README 和运行提示必须如实说明 DeepSeek 的数据使用政策，不能暗示有 ZDR。
- provider 抽象增加一层接口，但避免了未来把判定逻辑绑死在 DeepSeek 上。
