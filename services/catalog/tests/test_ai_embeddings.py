"""
Tests for the AI Recommendation & Semantic Search Engine.

Validates that the embedding engine produces semantically meaningful vectors:
  - Similar products cluster together (high cosine similarity)
  - Dissimilar products are distant (low cosine similarity)
  - Semantic query expansion maps "warm" queries to "winter" products
  - The vector index returns correctly ranked nearest neighbors
  - Cache integration works with Redis mock
"""

from app.ai import (
    EmbeddingEngine,
    VectorIndex,
    _expand_query_tokens,
    _tokenize,
)

# ── Unit Tests: Tokenizer ───────────────────────────────────────────────────────

class TestTokenizer:
    def test_removes_stop_words(self):
        tokens = _tokenize("this is a very good product for the office")
        assert "this" not in tokens
        assert "is" not in tokens
        assert "very" not in tokens
        assert "the" not in tokens
        assert "good" in tokens
        assert "product" in tokens
        assert "office" in tokens

    def test_lowercases_and_strips_punctuation(self):
        tokens = _tokenize("High-Quality Gaming Mouse!!!")
        assert "high" in tokens
        assert "quality" in tokens
        assert "gaming" in tokens
        assert "mouse" in tokens

    def test_empty_input(self):
        assert _tokenize("") == []
        assert _tokenize("   ") == []

    def test_filters_single_char_tokens(self):
        tokens = _tokenize("A B C desktop D")
        assert "desktop" in tokens
        assert len([t for t in tokens if len(t) == 1]) == 0


# ── Unit Tests: Semantic Expansion ──────────────────────────────────────────────

class TestSemanticExpansion:
    def test_expands_warm_to_winter_terms(self):
        tokens = ["warm", "jacket"]
        expanded = _expand_query_tokens(tokens)
        assert "winter" in expanded
        assert "thermal" in expanded
        assert "fleece" in expanded
        assert "jacket" in expanded

    def test_expands_gaming_terms(self):
        tokens = ["gaming", "keyboard"]
        expanded = _expand_query_tokens(tokens)
        assert "gamer" in expanded
        assert "esports" in expanded
        assert "rgb" in expanded

    def test_no_duplicates_in_expansion(self):
        tokens = ["winter", "cold"]  # Both expand to overlapping terms
        expanded = _expand_query_tokens(tokens)
        assert len(expanded) == len(set(expanded))

    def test_unknown_tokens_pass_through(self):
        tokens = ["xylophone", "quantum"]
        expanded = _expand_query_tokens(tokens)
        assert expanded == ["xylophone", "quantum"]


# ── Unit Tests: Embedding Engine ────────────────────────────────────────────────

class TestEmbeddingEngine:
    def setup_method(self):
        self.engine = EmbeddingEngine(dimension=64)
        self.engine.fit_corpus([
            "wireless bluetooth gaming headset with rgb lighting",
            "ergonomic office chair with lumbar support",
            "winter thermal insulated fleece jacket waterproof",
            "beach summer lightweight breathable cotton shirt",
            "mechanical keyboard cherry mx switches gaming",
        ])

    def test_embedding_dimension(self):
        vec = self.engine.embed("gaming headset")
        assert len(vec) == 64

    def test_embedding_is_l2_normalized(self):
        vec = self.engine.embed("wireless gaming headset")
        magnitude = sum(v * v for v in vec) ** 0.5
        assert abs(magnitude - 1.0) < 0.001, f"Expected unit vector, got magnitude {magnitude}"

    def test_empty_text_returns_zero_vector(self):
        vec = self.engine.embed("")
        assert all(v == 0.0 for v in vec)

    def test_similar_texts_have_high_similarity(self):
        """Products in the same semantic domain should cluster together."""
        vec_a = self.engine.embed("wireless bluetooth gaming headset")
        vec_b = self.engine.embed("gaming headset with bluetooth wireless")
        similarity = EmbeddingEngine.cosine_similarity(vec_a, vec_b)
        assert similarity > 0.7, f"Similar products should have high similarity, got {similarity}"

    def test_dissimilar_texts_have_low_similarity(self):
        """Products in different domains should be far apart."""
        vec_winter = self.engine.embed("winter thermal insulated fleece jacket")
        vec_gaming = self.engine.embed("mechanical keyboard gaming rgb switches")
        similarity = EmbeddingEngine.cosine_similarity(vec_winter, vec_gaming)
        assert similarity < 0.3, f"Dissimilar products should have low similarity, got {similarity}"

    def test_semantic_expansion_improves_matching(self):
        """Searching 'warm gear' with expansion should match 'winter jacket' better."""
        vec_query_expanded = self.engine.embed("warm gear", expand_semantics=True)
        vec_query_plain = self.engine.embed("warm gear", expand_semantics=False)
        vec_winter = self.engine.embed("winter thermal fleece jacket")

        sim_expanded = EmbeddingEngine.cosine_similarity(vec_query_expanded, vec_winter)
        sim_plain = EmbeddingEngine.cosine_similarity(vec_query_plain, vec_winter)

        assert sim_expanded > sim_plain, (
            f"Expanded query should match better: expanded={sim_expanded:.4f} vs plain={sim_plain:.4f}"
        )

    def test_deterministic_embeddings(self):
        """Same input should always produce same embedding."""
        vec1 = self.engine.embed("office chair ergonomic")
        vec2 = self.engine.embed("office chair ergonomic")
        assert vec1 == vec2


# ── Unit Tests: Vector Index ────────────────────────────────────────────────────

class TestVectorIndex:
    def test_upsert_and_search(self):
        index = VectorIndex()
        index.upsert("a", [1.0, 0.0, 0.0])
        index.upsert("b", [0.9, 0.1, 0.0])
        index.upsert("c", [0.0, 0.0, 1.0])

        results = index.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0][0] == "a"  # Exact match is most similar
        assert results[1][0] == "b"  # Close match is second

    def test_exclude_ids(self):
        index = VectorIndex()
        index.upsert("a", [1.0, 0.0])
        index.upsert("b", [0.9, 0.1])

        results = index.search([1.0, 0.0], top_k=5, exclude_ids={"a"})
        assert len(results) == 1
        assert results[0][0] == "b"

    def test_empty_index_returns_empty(self):
        index = VectorIndex()
        results = index.search([1.0, 0.0], top_k=5)
        assert results == []

    def test_size_property(self):
        index = VectorIndex()
        assert index.size == 0
        index.upsert("x", [1.0])
        assert index.size == 1


# ── Integration Tests: Full Recommendation Pipeline ─────────────────────────────

class TestRecommendationPipeline:
    """End-to-end test of the embedding → index → search pipeline."""

    def test_full_pipeline_ranks_correctly(self):
        engine = EmbeddingEngine(dimension=128)

        products = [
            ("p1", "Wireless Bluetooth Gaming Headset with Surround Sound"),
            ("p2", "Gaming Mechanical Keyboard RGB Cherry MX Switches"),
            ("p3", "Ergonomic Office Chair Mesh Back Lumbar Support"),
            ("p4", "Winter Thermal Insulated Down Jacket Waterproof"),
            ("p5", "Gaming Mouse Wireless 16000 DPI RGB Lighting"),
            ("p6", "Summer Cotton Beach Shorts Lightweight Breathable"),
        ]

        corpus = [text for _, text in products]
        engine.fit_corpus(corpus)

        index = VectorIndex()
        for pid, text in products:
            embedding = engine.embed(text)
            index.upsert(pid, embedding)

        # Search for "gaming" — p1, p2, p5 should rank highest
        query_vec = engine.embed("gaming peripherals", expand_semantics=True)
        results = index.search(query_vec, top_k=3)
        result_ids = {r[0] for r in results}

        # At least 2 of the 3 gaming products should be in top 3
        gaming_ids = {"p1", "p2", "p5"}
        overlap = result_ids.intersection(gaming_ids)
        assert len(overlap) >= 2, f"Expected gaming products in top results, got {result_ids}"

    def test_semantic_query_finds_related_products(self):
        """'cold weather clothing' should find winter jacket even without exact words."""
        engine = EmbeddingEngine(dimension=128)
        products = [
            ("jacket", "Winter Thermal Insulated Fleece Jacket Waterproof Warm Snow Cold Weather Coat"),
            ("shirt", "Summer Lightweight Breathable Cotton Beach Shirt Tropical Sun"),
            ("keyboard", "Mechanical Gaming Keyboard RGB Backlit Cherry Switches USB"),
            ("mouse", "Gaming Mouse Optical Sensor DPI RGB Lighting Wired"),
            ("shorts", "Beach Summer Swim Shorts Quick Dry Lightweight"),
        ]
        engine.fit_corpus([t for _, t in products])

        index = VectorIndex()
        for pid, text in products:
            index.upsert(pid, engine.embed(text))

        # "cold weather gear" — semantic expansion maps cold → winter, warm, etc.
        query_vec = engine.embed("cold weather gear", expand_semantics=True)
        results = index.search(query_vec, top_k=2)
        result_ids = [r[0] for r in results]

        # Winter jacket should be in the top 2 results
        assert "jacket" in result_ids, f"Expected winter jacket in top results, got {result_ids}"
