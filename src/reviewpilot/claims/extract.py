"""LLM-based atomic claim extraction with local schema validation."""

from __future__ import annotations

import json

from pydantic import ValidationError

from reviewpilot.domain import ExtractionResult, Sentence
from reviewpilot.llm.provider import LLMError, LLMProvider

EXTRACTION_INSTRUCTIONS = """\
你是技术文章的主张抽取器。你不做核验，也不使用任何外部知识。

任务：对输入的每个句子，找出其中可判定的原子技术主张。
- 可判定主张：API 签名、参数默认值、返回值、版本行为、性能数字、标准/协议规定等可以被文档支持或反驳的陈述。
- 不可判定内容：观点、预测、建议、定义、修辞、纯代码。

规则：
1. 每个输入句子必须在输出中出现一次，sentence_id 原样返回。
2. 可判定主张的 quote 必须是该句子中的逐字片段，包括标点和 Markdown 符号；不得改写、翻译、补全或添加文字。
3. 一句话有多个独立主张时返回多个 quote；不要把同一个主张拆成多个。
4. 如果主张描述的是某个函数/方法/参数的行为，quote 必须包含谓词或行为（例如“发送请求”“默认为 True”），不要只返回孤立的函数签名、参数名或代码标识符；除非整句本身只有一个标识符且没有可判定的行为。
5. 没有可判定主张时，返回一个 kind 为 opinion/prediction/definition/rhetoric/code/other 的条目，reason 说明原因。
6. 不要跨句合并，不要判断真假，不要引用外部知识。
7. 只输出符合给定 JSON schema 的对象。
"""


def extract_claims(
    provider: LLMProvider,
    sentences: list[Sentence],
    *,
    model: str,
    batch_size: int = 25,
) -> tuple[ExtractionResult, dict[str, int]]:
    all_sentences = []
    total_usage: dict[str, int] = {}

    for offset in range(0, len(sentences), batch_size):
        batch = sentences[offset : offset + batch_size]
        payload = [{"sentence_id": s.sentence_id, "text": s.text} for s in batch]
        user_input = json.dumps(payload, ensure_ascii=False, indent=2)
        instructions = EXTRACTION_INSTRUCTIONS

        for attempt in range(2):
            data, usage = provider.complete_json(
                model=model,
                instructions=instructions,
                input=user_input,
                schema=ExtractionResult.model_json_schema(),
                schema_name="claim_extraction",
                effort="none",
                max_output_tokens=4096,
                temperature=0.0,
            )
            for key, value in usage.items():
                total_usage[key] = total_usage.get(key, 0) + value
            try:
                parsed = ExtractionResult.model_validate(data)
                all_sentences.extend(parsed.sentences)
                break
            except ValidationError as exc:
                if attempt == 1:
                    raise LLMError(f"主张抽取输出不符合 schema：{exc}") from exc
                instructions = (
                    EXTRACTION_INSTRUCTIONS
                    + "\n上一次输出不符合 schema。请只返回符合 schema 的 JSON，不要解释。"
                )

    return ExtractionResult(sentences=all_sentences), total_usage
