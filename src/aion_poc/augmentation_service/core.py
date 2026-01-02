"""
Augmentation Module - Handles LLM integration and response generation.

This module provides the final layer of the RAG pipeline, taking retrieved 
context and generating coherent responses using LLMs.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator, AsyncIterator
from dataclasses import dataclass
import asyncio
import logging
import json
from time import perf_counter

import httpx  # type: ignore[import-not-found]

from ..logging_config import configure_logging


configure_logging()
LOGGER = logging.getLogger(__name__)


def _extract_ollama_error(response: Any) -> str:
    """Return a human readable error string from an Ollama HTTP response."""

    try:
        payload = response.json()
    except (ValueError, TypeError):  # pragma: no cover - defensive for malformed payloads
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("detail")
        if detail:
            return str(detail)
        return json.dumps(payload)[:200]

    text = getattr(response, "text", "")
    return str(text)[:200]


@dataclass
class AugmentationContext:
    """Context for LLM augmentation."""
    query: str
    retrieved_chunks: List[Any]  # RetrievalResult objects
    metadata: Dict[str, Any]
    system_prompt: Optional[str] = None


@dataclass
class AugmentationResponse:
    """Response from LLM augmentation."""
    answer: str
    sources: List[str]
    confidence: float
    metadata: Dict[str, Any]
    reasoning: Optional[str] = None


class BaseLLM(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get("model") or config.get("model_name", "llama3:8b")
        self.available_models: List[str] = config.get("available_models", [])
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", config.get("max_output_tokens", 1000))
        self.timeout = config.get("timeout") or config.get("timeout_seconds", 120)
        LOGGER.debug(
            "LLM base configured",
            extra={
                "model_name": self.model_name,
                "available_models": self.available_models[:5],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "timeout_seconds": self.timeout,
                "provider": self.__class__.__name__,
            },
        )
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from prompt."""
        raise NotImplementedError
    
    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response generation."""
        raise NotImplementedError


class OllamaLLM(BaseLLM):
    """
    Ollama LLM implementation - Primary choice for local development.
    Uses your existing Ollama setup.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = (
            config.get("base_url")
            or config.get("ollama_url")
            or "http://localhost:11434"
        ).rstrip("/")
        LOGGER.info(
            "Initialized Ollama provider",
            extra={"model": self.model_name, "base_url": self.base_url},
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Ollama."""

        model = kwargs.get("model") or self.model_name
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        timeout = kwargs.get("timeout", self.timeout)
        request_started = perf_counter()

        LOGGER.info(
            "Dispatching Ollama completion request",
            extra={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout,
                "base_url": self.base_url,
            },
        )
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Ollama prompt snapshot",
                extra={"prompt_length": len(prompt), "prompt_preview": prompt[:160]},
            )

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                if response.status_code == 404:
                    detail = _extract_ollama_error(response)
                    message = detail or "Requested model is not available on the Ollama server."
                    LOGGER.error(
                        "Ollama model not found",
                        extra={"model": model, "base_url": self.base_url, "detail": detail},
                    )
                    raise RuntimeError(
                        f"Ollama returned 404 for model '{model}'. {message}"
                    )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            LOGGER.exception(
                "Ollama generate failed",
                extra={"error": str(exc), "base_url": self.base_url, "model": model},
            )
            raise

        duration_ms = (perf_counter() - request_started) * 1000
        LOGGER.info(
            "Ollama completion received",
            extra={
                "model": model,
                "duration_ms": round(duration_ms, 2),
                "response_keys": list(data.keys())[:5],
            },
        )
        answer = data.get("response") or data.get("message", "")
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Ollama completion preview",
                extra={
                    "answer_tokens": len(answer.split()),
                    "answer_preview": answer[:160],
                },
            )
        return answer.strip()
    
    def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response from Ollama."""

        model = kwargs.get("model") or self.model_name
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        timeout = kwargs.get("timeout", self.timeout)
        request_started = perf_counter()

        LOGGER.info(
            "Starting Ollama streaming request",
            extra={
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout,
                "base_url": self.base_url,
            },
        )
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Ollama streaming prompt snapshot",
                extra={"prompt_length": len(prompt), "prompt_preview": prompt[:160]},
            )

        async def generator() -> AsyncGenerator[str, None]:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/api/generate",
                        json=payload,
                    ) as response:
                        if response.status_code == 404:
                            detail = _extract_ollama_error(response)
                            message = detail or "Requested model is not available on the Ollama server."
                            LOGGER.error(
                                "Ollama model not found",
                                extra={"model": model, "base_url": self.base_url, "detail": detail},
                            )
                            raise RuntimeError(
                                f"Ollama returned 404 for model '{model}'. {message}"
                            )
                        response.raise_for_status()
                        chunk_count = 0
                        total_chars = 0
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError:
                                LOGGER.debug(
                                    "Skipping malformed Ollama stream chunk",
                                    extra={"chunk_preview": line[:80]},
                                )
                                continue

                            content = chunk.get("response")
                            if content:
                                chunk_count += 1
                                total_chars += len(content)
                                yield content

                            if chunk.get("done"):
                                duration_ms = (perf_counter() - request_started) * 1000
                                LOGGER.info(
                                    "Ollama streaming completed",
                                    extra={
                                        "model": model,
                                        "duration_ms": round(duration_ms, 2),
                                        "chunks": chunk_count,
                                        "characters": total_chars,
                                    },
                                )
                                break
            except httpx.HTTPError as exc:
                LOGGER.exception(
                    "Ollama streaming failed",
                    extra={"error": str(exc), "base_url": self.base_url, "model": model},
                )
                raise

        return generator()


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("openai_api_key")
        self.model_name = config.get("model", config.get("model_name", self.model_name))
        LOGGER.info(
            "Initialized OpenAI provider",
            extra={"model": self.model_name, "api_key_present": bool(self.api_key)},
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI."""
        # NOTE: Implement OpenAI API integration when credentials are configured.
        # import openai
        # openai.api_key = self.api_key
        
        # response = await openai.ChatCompletion.acreate(
        #     model=self.model_name,
        #     messages=[{"role": "user", "content": prompt}],
        #     temperature=kwargs.get("temperature", self.temperature),
        #     max_tokens=kwargs.get("max_tokens", self.max_tokens)
        # )
        # 
        # return response.choices[0].message.content
        
        return f"[OpenAI {self.model_name} response to: {prompt[:100]}...]"
    
    def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response from OpenAI."""
        # NOTE: Implement OpenAI streaming once API integration is added.

        async def generator() -> AsyncGenerator[str, None]:
            response = await self.generate(prompt, **kwargs)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.05)

        return generator()


class AnthropicLLM(BaseLLM):
    """Anthropic LLM implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("anthropic_api_key")
        self.model_name = config.get("model", config.get("model_name", self.model_name))
        LOGGER.info(
            "Initialized Anthropic provider",
            extra={"model": self.model_name, "api_key_present": bool(self.api_key)},
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic."""
        # NOTE: Implement Anthropic API wiring when available.
        return f"[Anthropic {self.model_name} response to: {prompt[:100]}...]"
    
    def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response from Anthropic."""

        async def generator() -> AsyncGenerator[str, None]:
            response = await self.generate(prompt, **kwargs)
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.05)

        return generator()


class PromptTemplate:
    """Manages prompt templates for different use cases."""
    
    def __init__(self):
        self.templates = {
            "qa": self._qa_template(),
            "summarization": self._summarization_template(),
            "troubleshooting": self._troubleshooting_template(),
            "explanation": self._explanation_template()
        }
    
    def _qa_template(self) -> str:
        """Question answering template."""
        return """You are an expert AI assistant for ChargePoint charging station systems. Answer the question based on the provided context.

        Context:
        {context}

        Question: {query}

        Instructions:
        - Provide a clear, accurate answer based on the context
        - If the information is not in the context, say so
        - Include relevant technical details
        - Mention source documents when helpful

        Answer:"""
    
    def _troubleshooting_template(self) -> str:
        """Troubleshooting template."""
        return """You are a technical expert for ChargePoint charging station troubleshooting. Help diagnose and resolve the issue based on the provided documentation.

        Context:
        {context}

        Issue: {query}

        Instructions:
        - Provide step-by-step troubleshooting guidance
        - Start with the most likely causes
        - Include safety warnings if relevant
        - Reference specific error codes or symptoms
        - Suggest when to contact support

        Troubleshooting Steps:"""
    
    def _summarization_template(self) -> str:
        """Document summarization template."""
        return """Summarize the key points from the following ChargePoint charging station documentation.
        
        Content:
        {context}

        Focus: {query}

        Provide a concise summary covering:
        - Main points related to the focus area
        - Important technical specifications
        - Key procedures or steps
        - Relevant warnings or notes

        Summary:"""
    
    def _explanation_template(self) -> str:
        """Technical explanation template."""
        return """You are a technical expert explaining ChargePoint charging station concepts. Provide a clear explanation based on the documentation.

        Documentation:
        {context}

        Topic to explain: {query}

        Instructions:
        - Explain the concept clearly for both technical and non-technical users
        - Use examples where helpful
        - Include relevant technical details
        - Break down complex topics into understandable parts

        Explanation:"""
    
    def get_template(self, template_type: str) -> str:
        """Get template by type."""
        return self.templates.get(template_type, self.templates["qa"])
    
    def format_prompt(self, template_type: str, query: str, context: str, **kwargs) -> str:
        """Format template with variables."""
        template = self.get_template(template_type)
        return template.format(query=query, context=context, **kwargs)


class AugmentationEngine:
    """
    Main augmentation engine that coordinates LLM interaction.
    Handles prompt construction, response generation, and post-processing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = config.get("llm", {})
        self.provider = self.llm_config.get("provider", "ollama")
        self.default_model = (
            self.llm_config.get("model")
            or self.llm_config.get("model_name")
            or "llama3:8b"
        )
        self.available_models = self.llm_config.get("available_models", [])
        
        # Initialize LLM providers
        self.llms = {
            "ollama": OllamaLLM(self.llm_config),
            "openai": OpenAILLM(self.llm_config),
            "anthropic": AnthropicLLM(self.llm_config)
        }
        
        self.prompt_template = PromptTemplate()
        
        # Response configuration
        self.max_context_length = config.get("max_context_length", 4000)
        self.include_sources = config.get("include_sources", True)
        LOGGER.info(
            "Augmentation engine configured",
            extra={
                "provider": self.provider,
                "default_model": self.default_model,
                "available_models": self.available_models[:5],
                "max_context_length": self.max_context_length,
                "include_sources": self.include_sources,
            },
        )
    
    async def augment(
        self,
        context: AugmentationContext,
        template_type: str = "qa",
        stream: bool = False
    ) -> AugmentationResponse:
        """
        Generate augmented response from context.
        
        Args:
            context: Augmentation context with query and retrieved chunks
            template_type: Type of prompt template to use
            stream: Whether to stream the response
            
        Returns:
            Augmented response with answer and metadata
        """
        LOGGER.info(
            "Augmentation request received",
            extra={
                "query_preview": context.query[:120],
                "provider": self.provider,
                "template_type": template_type,
                "context_chunks": len(context.retrieved_chunks),
                "stream": stream,
            },
        )
        start_time = perf_counter()

        # Get LLM
        llm = self.llms.get(self.provider)
        if not llm:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        requested_model = context.metadata.get("llm_model")
        selected_model = requested_model or self.default_model
        if self.available_models and selected_model not in self.available_models:
            LOGGER.warning(
                "Requested LLM model unavailable; using default",
                extra={
                    "requested_model": requested_model,
                    "default_model": self.default_model,
                    "available_models": self.available_models,
                },
            )
            selected_model = self.default_model

        generation_kwargs = {
            "model": selected_model,
            "temperature": self.llm_config.get("temperature", getattr(llm, "temperature", 0.1)),
            "max_tokens": self.llm_config.get("max_output_tokens", getattr(llm, "max_tokens", 1000)),
            "timeout": self.llm_config.get("timeout_seconds", getattr(llm, "timeout", 120)),
        }
        
        # Prepare context for prompt
        formatted_context = self._format_context(context.retrieved_chunks)
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Prompt context prepared",
                extra={
                    "formatted_length": len(formatted_context),
                    "original_chunks": len(context.retrieved_chunks),
                },
            )
        
        # Build prompt
        prompt = self.prompt_template.format_prompt(
            template_type=template_type,
            query=context.query,
            context=formatted_context
        )
        LOGGER.debug(
            "Prompt generated",
            extra={
                "selected_model": selected_model,
                "token_estimate": len(prompt.split()),
                "template_type": template_type,
            },
        )
        
        # Generate response
        try:
            if stream:
                answer_parts = []
                async for chunk in llm.stream_generate(prompt, **generation_kwargs):
                    answer_parts.append(chunk)
                answer = "".join(answer_parts)
            else:
                answer = await llm.generate(prompt, **generation_kwargs)
        except Exception as exc:  # pragma: no cover - depends on provider
            LOGGER.exception(
                "LLM generation failed",
                extra={"error": str(exc), "provider": self.provider},
            )
            raise
        
        # Extract sources
        sources = self._extract_sources(context.retrieved_chunks)
        
        # Calculate confidence (simple heuristic)
        confidence = self._calculate_confidence(context.retrieved_chunks, answer)

        duration_ms = (perf_counter() - start_time) * 1000
        LOGGER.info(
            "Augmentation completed",
            extra={
                "provider": self.provider,
                "duration_ms": round(duration_ms, 2),
                "model": selected_model,
                "answer_tokens": len(answer.split()),
                "sources": len(sources),
                "confidence": round(confidence, 4),
            },
        )
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "Augmentation answer preview",
                extra={"answer_preview": answer[:160]},
            )
        
        return AugmentationResponse(
            answer=answer.strip(),
            sources=sources,
            confidence=confidence,
            metadata={
                "llm_provider": self.provider,
                "llm_model": generation_kwargs["model"],
                "llm_available_models": self.available_models,
                "template_type": template_type,
                "context_chunks": len(context.retrieved_chunks),
                "prompt_tokens": len(prompt.split()),
                "response_tokens": len(answer.split()),
                "llm_timeout_seconds": generation_kwargs["timeout"],
            }
        )
    
    async def stream_augment(
        self,
        context: AugmentationContext,
        template_type: str = "qa"
    ) -> AsyncGenerator[str, None]:
        """Stream augmented response."""
        LOGGER.info(
            "Streaming augmentation requested",
            extra={
                "query_preview": context.query[:120],
                "provider": self.provider,
                "template_type": template_type,
                "context_chunks": len(context.retrieved_chunks),
            },
        )
        llm = self.llms.get(self.provider)
        if not llm:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        requested_model = context.metadata.get("llm_model")
        selected_model = requested_model or self.default_model
        if self.available_models and selected_model not in self.available_models:
            LOGGER.warning(
                "Requested LLM model unavailable; using default",
                extra={
                    "requested_model": requested_model,
                    "default_model": self.default_model,
                    "available_models": self.available_models,
                },
            )
            selected_model = self.default_model

        generation_kwargs = {
            "model": selected_model,
            "temperature": self.llm_config.get("temperature", getattr(llm, "temperature", 0.1)),
            "max_tokens": self.llm_config.get("max_output_tokens", getattr(llm, "max_tokens", 1000)),
            "timeout": self.llm_config.get("timeout_seconds", getattr(llm, "timeout", 120)),
        }
        
        formatted_context = self._format_context(context.retrieved_chunks)
        prompt = self.prompt_template.format_prompt(
            template_type=template_type,
            query=context.query,
            context=formatted_context,
        )

        try:
            async for chunk in llm.stream_generate(prompt, **generation_kwargs):
                yield chunk
        except Exception as exc:  # pragma: no cover - depends on provider
            LOGGER.exception(
                "Streaming augmentation failed",
                extra={"error": str(exc), "provider": self.provider},
            )
            raise
    
    def _format_context(self, retrieved_chunks: List[Any]) -> str:
        """Format retrieved chunks into context string."""
        if not retrieved_chunks:
            LOGGER.warning("No retrieved chunks supplied for augmentation context")
            return "No relevant context found."
        
        context_parts: List[str] = []
        current_length = 0
        
        for chunk in retrieved_chunks:
            metadata = getattr(chunk, "metadata", {}) or {}
            content = (
                getattr(chunk, "page_content", None)
                or getattr(chunk, "content", None)
                or getattr(chunk, "snippet", None)
                or metadata.get("chunk")
                or "[No content available]"
            )

            source = (
                getattr(chunk, "source_document", None)
                or metadata.get("source")
                or metadata.get("source_file")
                or metadata.get("source_path")
                or metadata.get("document_id")
                or "Unknown source"
            )

            score = getattr(chunk, "score", metadata.get("score"))
            score_line = f"Score: {round(score, 4)}\n" if isinstance(score, (int, float)) else ""

            chunk_text = f"Source: {source}\n{score_line}{content}\n"

            if current_length + len(chunk_text) > self.max_context_length:
                LOGGER.debug(
                    "Context truncated",
                    extra={
                        "max_context_length": self.max_context_length,
                        "included_chunks": len(context_parts),
                        "attempted_length": current_length + len(chunk_text),
                    },
                )
                break

            context_parts.append(chunk_text)
            current_length += len(chunk_text)
        
        LOGGER.debug(
            "Context formatted",
            extra={
                "total_chunks": len(context_parts),
                "total_length": current_length,
            },
        )
        return "\n---\n".join(context_parts)
    
    def _extract_sources(self, retrieved_chunks: List[Any]) -> List[str]:
        """Extract unique source documents."""
        if not self.include_sources:
            return []
        
        sources = []
        seen_sources = set()
        
        for chunk in retrieved_chunks:
            metadata = getattr(chunk, "metadata", {}) or {}
            source = getattr(chunk, "source_document", None) or metadata.get("source_file") or metadata.get("source_path")
            if source and source not in seen_sources:
                sources.append(source)
                seen_sources.add(source)

        LOGGER.debug(
            "Sources extracted from chunks",
            extra={"total_sources": len(sources)},
        )
        
        return sources
    
    def _calculate_confidence(
        self, 
        retrieved_chunks: List[Any], 
        answer: str
    ) -> float:
        """Calculate confidence score for the response."""
        if not retrieved_chunks:
            return 0.0
        
        # Simple heuristic based on:
        # - Average retrieval scores
        # - Number of chunks
        # - Answer length
        
        scores = [getattr(chunk, "score", getattr(chunk, "metadata", {}).get("score", 0.0)) for chunk in retrieved_chunks]
        avg_score = sum(scores) / len(retrieved_chunks)
        chunk_factor = min(len(retrieved_chunks) / 3.0, 1.0)  # Normalize to max 3 chunks
        answer_factor = min(len(answer.split()) / 50.0, 1.0)  # Normalize to ~50 words
        
        confidence = (avg_score * 0.6 + chunk_factor * 0.2 + answer_factor * 0.2)
        LOGGER.debug(
            "Confidence calculated",
            extra={
                "avg_score": round(avg_score, 4),
                "chunk_factor": round(chunk_factor, 4),
                "answer_factor": round(answer_factor, 4),
                "confidence": round(confidence, 4),
            },
        )
        return max(0.0, min(1.0, confidence))


class AugmentationManager:
    """
    High-level interface for augmentation operations.
    Coordinates between retrieval and LLM components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = AugmentationEngine(config)
        LOGGER.info("Augmentation manager initialized")
    
    async def generate_answer(
        self, 
        query: str, 
        retrieved_results: List[Any],
        answer_type: str = "qa",
        llm_model: Optional[str] = None,
    ) -> AugmentationResponse:
        """Generate answer from query and retrieved results."""
        metadata = {"answer_type": answer_type}
        if llm_model:
            metadata["llm_model"] = llm_model

        context = AugmentationContext(
            query=query,
            retrieved_chunks=retrieved_results,
            metadata=metadata,
        )
        LOGGER.info(
            "Generating augmented answer",
            extra={
                "query_preview": query[:120],
                "answer_type": answer_type,
                "retrieved_results": len(retrieved_results),
                "llm_model": llm_model or "(default)",
            },
        )

        return await self.engine.augment(context, template_type=answer_type)
    
    async def stream_answer(
        self, 
        query: str, 
        retrieved_results: List[Any],
        answer_type: str = "qa",
        llm_model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream answer generation."""
        metadata = {"answer_type": answer_type}
        if llm_model:
            metadata["llm_model"] = llm_model

        context = AugmentationContext(
            query=query,
            retrieved_chunks=retrieved_results,
            metadata=metadata,
        )
        LOGGER.info(
            "Streaming augmented answer",
            extra={
                "query_preview": query[:120],
                "answer_type": answer_type,
                "retrieved_results": len(retrieved_results),
                "llm_model": llm_model or "(default)",
            },
        )

        async for chunk in self.engine.stream_augment(context, template_type=answer_type):
            yield chunk
    
    def detect_query_type(self, query: str) -> str:
        """Detect appropriate template type from query."""
        normalized = " ".join(query.lower().split())
        is_question = query.strip().endswith("?")

        def contains_any(phrases: List[str]) -> bool:
            return any(phrase in normalized for phrase in phrases)

        summarization_markers = ["summarize", "summary", "overview", "brief", "outline"]
        explanation_markers = [
            "what is",
            "what does",
            "meaning of",
            "explain",
            "describe",
            "how does",
            "why does",
            "difference between",
        ]
        troubleshooting_markers = [
            "not working",
            "error",
            "issue",
            "problem",
            "fault",
            "fail",
            "troubleshoot",
        ]
        troubleshooting_actions = [
            "fix",
            "resolve",
            "steps",
            "repair",
            "reset",
            "workaround",
            "how do i",
            "how to",
        ]

        if contains_any(summarization_markers):
            return "summarization"

        if contains_any(explanation_markers):
            return "explanation"

        if contains_any(troubleshooting_markers):
            has_action_language = contains_any(troubleshooting_actions)
            if not is_question or has_action_language:
                return "troubleshooting"
            # Questions such as "What does error code X mean" are explanatory
            return "explanation"

        return "qa"