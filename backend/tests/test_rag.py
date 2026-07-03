"""RAG 切片和检索测试"""
from rag.chunker import DocumentChunker


class TestDocumentChunker:
    def test_basic_chunking(self):
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=20, min_chunk_size=10)
        text = "This is a test document. " * 50
        chunks = chunker.chunk(text, source="test.md")
        assert len(chunks) > 0
        for c in chunks:
            assert "content" in c
            assert c["source"] == "test.md"

    def test_header_splitting(self):
        chunker = DocumentChunker(chunk_size=500, min_chunk_size=10)
        text = """## Section 1
Some content here.

## Section 2
More content there."""
        chunks = chunker.chunk(text, source="test.md")
        # Should split at ## headers
        contents = [c["content"] for c in chunks]
        assert any("Section 1" in c for c in contents)

    def test_short_text(self):
        chunker = DocumentChunker(chunk_size=500, min_chunk_size=100)
        text = "Too short"
        chunks = chunker.chunk(text, source="test.md")
        assert len(chunks) == 0  # Below min_chunk_size

    def test_sliding_window_overlap(self):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=30, min_chunk_size=10)
        text = "A" * 200
        chunks = chunker.chunk(text, source="test.md")
        assert len(chunks) >= 2

    def test_chinese_text(self):
        chunker = DocumentChunker(chunk_size=200, min_chunk_size=10)
        text = "手术床背板驱动电机过载保护触发。电流超出正常工作范围。需要检查导轨润滑状态。"
        chunks = chunker.chunk(text, source="test.md")
        assert len(chunks) >= 1

    def test_merge_short_chunks(self):
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=20, min_chunk_size=10)
        text = "A" * 50 + "\n\n" + "B" * 50 + "\n\n" + "C" * 50
        chunks = chunker.chunk(text, source="test.md")
        # Short paragraphs should be merged
        assert len(chunks) <= 1  # All short, merged into one
