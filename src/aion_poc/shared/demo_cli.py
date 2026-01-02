"""
AION RAG CLI Demo - command-line interface for exercising the pipeline.

This keeps the interactive harness separate from any future UI surfaces.
Run with: python -m aion_poc.shared.demo_cli
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
import time
from typing import Optional

from .pipeline import DemoPipeline, get_pipeline, initialize_pipeline
from ..config.settings import get_settings
from ..logging_config import configure_logging

configure_logging()
LOGGER = logging.getLogger(__name__)

CLI_HANDLED_EXCEPTIONS = (RuntimeError, ValueError, OSError)


class AionDemo:
    """Interactive demo for AION RAG system."""

    def __init__(self):
        self.pipeline: Optional[DemoPipeline] = None
        self.config = get_settings()
        LOGGER.debug(
            "CLI demo initialized",
            extra={
                "embedding_model": getattr(self.config.embedding, "model", None),
                "vector_collection": getattr(self.config.vectorstore, "collection", None),
            },
        )

    def print_banner(self):
        """Print demo banner."""
        banner = """
╔══════════════════════════════════════════════════╗
║               AION RAG SYSTEM DEMO               ║
║          Advanced RAG for Charging Stations      ║
╠══════════════════════════════════════════════════╣
║ Features:                                        ║
║ ✅ Multi-source ingestion (JIRA, PDF, Confluence)║
║ ✅ Semantic chunking with similarity boundaries  ║
║ ✅ Multi-provider embeddings                     ║
║ ✅ Layered retrieval with fusion                 ║
║ ✅ Multi-LLM augmentation                        ║
╚══════════════════════════════════════════════════╝
        """
        print(banner)

    def print_menu(self):
        """Print main menu."""
        menu = """
📋 DEMO MENU:
1. 📄 Ingest Sample Documents
2. 🔍 Query Knowledge Base
3. 📊 Show System Statistics  
4. 🩺 Health Check
5. ⚙️  Show Configuration
6. 🚪 Exit

Choose an option (1-6): """
        return input(menu).strip()

    async def initialize_system(self):
        """Initialize the RAG pipeline."""
        print("🚀 Initializing AION RAG system...")
        LOGGER.info("Starting CLI pipeline initialization")
        init_start = time.perf_counter()

        try:
            initialize_pipeline()
            self.pipeline = get_pipeline()
            LOGGER.info("Pipeline initialized", extra={"pipeline_ready": self.pipeline is not None})
            LOGGER.debug(
                "Pipeline initialization timing",
                extra={"duration_seconds": round(time.perf_counter() - init_start, 3)},
            )

            # Check health
            health = await self.pipeline.health_check()
            if health["overall"] == "healthy":
                print("✅ System initialized successfully!")
                LOGGER.info("Pipeline health check passed")
            else:
                print(f"⚠️  System initialized with issues: {health['overall']}")
                for component, status in health["components"].items():
                    if status != "healthy":
                        print(f"   - {component}: {status}")
                LOGGER.warning(
                    "Pipeline initialized with warnings",
                    extra={"overall_status": health["overall"], "component_status": health["components"]},
                )
            LOGGER.debug("Health check snapshot", extra=health)

        except CLI_HANDLED_EXCEPTIONS as e:
            print(f"❌ Initialization failed: {e}")
            LOGGER.exception("Pipeline initialization failed", extra={"error": str(e)})
            sys.exit(1)

    async def ingest_sample_documents(self):
        """Ingest sample charging station documents."""
        print("📄 Preparing to ingest sample documents...")
        LOGGER.info("CLI requested sample document ingestion")

        if self.pipeline is None:
            LOGGER.error("Pipeline not initialized prior to ingestion request")
            raise RuntimeError("Pipeline must be initialized before ingesting documents")

        # Create sample documents directory
        docs_dir = Path("./data/sample_docs")
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Create sample documents if they don't exist
        sample_docs = [
            {
                "filename": "troubleshooting_guide.txt",
                "content": """AION Charging Station Troubleshooting Guide

Common Issues and Solutions:

1. Station Not Responding
   - Check power connection and LED indicators
   - Verify network connectivity (WiFi/Ethernet)
   - Reset station using main breaker (30 seconds)
   - Contact support if issue persists

2. Card Reader Errors
   - Clean card reader with soft, dry cloth
   - Check for physical damage or debris
   - Test with multiple cards
   - Replace reader if consistently failing

3. Charging Cable Locked
   - Use emergency release button (red button near connector)
   - Check for error codes on display
   - Manual unlock procedure: Hold unlock for 10 seconds
   - Call support for persistent lock issues

4. Display Issues
   - Blank display: Check power and reset station
   - Flickering: Update firmware via admin panel
   - Touch response: Clean screen with approved cleaner
   - Replace display unit if hardware failure confirmed

Error Codes:
- E001: Communication error - Check network connection
- E002: Ground fault detected - Inspect wiring, call electrician
- E003: Overvoltage condition - Check input voltage (208-240V)
- E004: Undervoltage condition - Verify adequate power supply
- E005: Temperature alarm - Check ventilation and ambient temp
- E006: Authentication failed - Verify card/app credentials

Maintenance Schedule:
- Daily: Visual inspection of station and cables
- Weekly: Clean connectors and display
- Monthly: Check mounting and hardware tightness  
- Quarterly: Software updates and log review
- Annually: Professional electrical inspection
                """
            },
            {
                "filename": "installation_manual.txt",
                "content": """AION Charging Station Installation Manual

Pre-Installation Requirements:
1. Electrical supply: 240V, 40A minimum
2. Network connection: Ethernet or WiFi
3. Mounting surface: Concrete or steel post
4. Clearance: 36 inches on all sides
5. Weather protection rating: IP65

Installation Steps:

1. Site Preparation
   - Mark mounting locations per site plan
   - Install electrical conduit and wiring
   - Ensure proper grounding per NEC guidelines
   - Test electrical connections before mounting

2. Physical Mounting
   - Anchor station to mounting surface using provided bolts
   - Torque specifications: 85 ft-lbs for main bolts
   - Install weather sealing gaskets
   - Verify station is level and secure

3. Electrical Connections
   - Connect L1, L2, L3 power lines to main terminals
   - Install ground wire to chassis ground point
   - Connect control wires for network communication
   - Install GFCI protection as required by code

4. Network Configuration
   - Connect Ethernet cable or configure WiFi
   - Set IP address via admin interface
   - Configure cloud connectivity settings
   - Test remote monitoring functionality

5. Commissioning
   - Power on station and verify startup sequence
   - Test all safety systems (GFCI, contactors)
   - Perform test charge with compatible vehicle
   - Calibrate energy metering if applicable
   - Complete installation checklist and documentation

Safety Notes:
- All electrical work must be performed by licensed electrician
- Follow local electrical codes and permits
- Test GFCI functionality monthly
- Maintain proper documentation for warranty
                """
            },
            {
                "filename": "user_manual.txt",
                "content": """AION Charging Station User Guide

Getting Started:
1. Park vehicle properly aligned with charging port
2. Present RFID card or open mobile app
3. Wait for authentication confirmation (green light)
4. Connect charging cable to vehicle
5. Charging will start automatically

Using RFID Cards:
- Hold card within 2 inches of reader
- Wait for beep and green light confirmation
- Remove card after session starts
- Keep card clean and undamaged for best results

Using Mobile App:
- Download AION ChargePoint app
- Create account and add payment method
- Scan QR code on station or select from map
- Follow in-app instructions to start session

Charging Process:
- LED indicators show charging status
- Blue light: Ready to connect
- Green light: Charging active  
- Red light: Error condition
- White light: Session complete

Ending Your Session:
1. Stop charging from app or press stop button
2. Wait for "Session Complete" message
3. Disconnect cable from vehicle first
4. Return cable to holster
5. Session summary will be sent via email/app

Troubleshooting:
- Card not working: Clean card and try again
- App connection issues: Check internet connectivity
- Cable won't release: Press emergency release button
- Charging not starting: Check vehicle compatibility

Customer Support:
- Phone: 1-800-AION-HELP
- Email: support@aioncharging.com
- Chat: Available 24/7 through mobile app
- Emergency: Use red emergency button on station

Pricing and Payment:
- Standard rate: $0.25/kWh
- Time-based parking after full charge: $1.00/hour
- Monthly subscription plans available
- All major credit cards accepted
                """
            }
        ]

        # Write sample documents
        created_files = []
        for doc in sample_docs:
            file_path = docs_dir / doc["filename"]
            try:
                file_path.write_text(doc["content"], encoding="utf-8")
            except OSError as exc:
                LOGGER.exception("Failed to write sample document", extra={"path": str(file_path), "error": str(exc)})
                raise
            created_files.append(str(file_path))
            LOGGER.debug("Sample document written", extra={"path": str(file_path), "bytes": len(doc["content"])})

        LOGGER.debug(
            "Sample documents prepared",
            extra={"count": len(created_files), "target_dir": str(docs_dir)},
        )

        print(f"📝 Created {len(created_files)} sample documents")

        # Prepare sources for ingestion
        sources = [
            {"type": "file", "source": file_path}
            for file_path in created_files
        ]

        # Ingest documents
        print("🔄 Starting ingestion process...")
        try:
            ingest_start = time.perf_counter()
            stats = await self.pipeline.ingest_documents(sources)
            LOGGER.debug(
                "Document ingestion timing",
                extra={"duration_seconds": round(time.perf_counter() - ingest_start, 3)},
            )

            LOGGER.info(
                "Sample ingestion completed",
                extra={
                    "documents": stats.total_documents,
                    "chunks": stats.total_chunks,
                    "total_time": round(stats.total_time, 2),
                },
            )
            LOGGER.debug(
                "Ingestion statistics",
                extra={
                    "ingestion_time": stats.ingestion_time,
                    "embedding_time": stats.embedding_time,
                    "storage_time": stats.storage_time,
                },
            )

            print(f"""
✅ Ingestion Complete!
📊 Statistics:
   - Documents processed: {stats.total_documents}
   - Chunks created: {stats.total_chunks}
   - Ingestion time: {stats.ingestion_time:.2f}s
   - Embedding time: {stats.embedding_time:.2f}s
   - Storage time: {stats.storage_time:.2f}s
   - Total time: {stats.total_time:.2f}s
            """)

        except CLI_HANDLED_EXCEPTIONS as e:
            print(f"❌ Ingestion failed: {e}")
            LOGGER.exception("Sample ingestion failed", extra={"error": str(e)})

    async def query_knowledge_base(self):
        """Interactive query interface."""
        print("\n🔍 QUERY KNOWLEDGE BASE")
        print("Type 'back' to return to main menu\n")
        LOGGER.info("CLI entered query workflow")

        if self.pipeline is None:
            LOGGER.error("Pipeline not initialized before query workflow")
            raise RuntimeError("Pipeline must be initialized before querying")

        # Sample queries for easy testing
        sample_queries = [
            "What should I do if the charging station is not responding?",
            "How do I use an RFID card to start charging?",
            "What does error code E002 mean?",
            "What is the maintenance schedule for charging stations?",
            "How do I install a new charging station?",
            "What are the electrical requirements for installation?"
        ]

        print("📋 Sample Queries (or type your own):")
        for i, query in enumerate(sample_queries, 1):
            print(f"{i}. {query}")
        print()

        while True:
            user_input = input("Enter your question (or number 1-6, or 'back'): ").strip()

            if user_input.lower() == 'back':
                break

            # Handle numbered selections
            if user_input.isdigit():
                num = int(user_input)
                if 1 <= num <= len(sample_queries):
                    query = sample_queries[num - 1]
                else:
                    print("❌ Invalid selection")
                    continue
            else:
                query = user_input

            if not query:
                continue

            print(f"\n🎯 Query: {query}")
            print("⏳ Processing...")
            LOGGER.info("Executing CLI query", extra={"query": query})
            LOGGER.debug("Query request metadata", extra={"strategy": "hybrid", "top_k": 3})

            try:
                query_start = time.perf_counter()
                strategy = "vectorstore"
                response = await self.pipeline.query(
                    query=query,
                    strategy=strategy,
                    top_k=3
                )
                if not response.sources and strategy == "vectorstore":
                    LOGGER.info(
                        "Vector store returned no results, falling back to in-memory index",
                        extra={"query": query},
                    )
                    response = await self.pipeline.query(
                        query=query,
                        strategy="demo",
                        top_k=3,
                    )
                LOGGER.debug(
                    "Pipeline query timing",
                    extra={"duration_seconds": round(time.perf_counter() - query_start, 3)},
                )

                print("""
✅ Answer:
""")
                print(response.answer)
                print("""
📚 Sources:
""")
                for source in response.sources:
                    print(f"- {source}")
                print(
                    """
📈 Metadata:
"""
                )
                for key, value in response.metadata.items():
                    print(f"- {key}: {value}")

            except CLI_HANDLED_EXCEPTIONS as e:
                print(f"❌ Query failed: {e}")
                LOGGER.exception("Query execution failed", extra={"error": str(e)})

    async def show_system_statistics(self):
        """Display ingestion metrics and vector store state."""

        if self.pipeline is None:
            raise RuntimeError("Pipeline is not initialized")

        stats = await self.pipeline.get_system_stats()
        pipeline_stats = stats.get("pipeline_stats", {})
        vector_store = stats.get("vector_store", {})
        corpus_profile = stats.get("corpus_profile", {})
        corpus_report = stats.get("corpus_report", {})
        query_metrics = stats.get("query_metrics", {})
        recent_queries = stats.get("recent_queries", [])
        alerts = stats.get("alerts", [])
        configuration = stats.get("configuration", {})

        print("""
📊 SYSTEM STATISTICS
--------------------
Pipeline Stats:
""")
        if pipeline_stats:
            for key, value in pipeline_stats.items():
                print(f"- {key.replace('_', ' ').title()}: {value}")
        else:
            print("- No pipeline data available")

        print("\nVector Store:")
        if vector_store:
            for key, value in vector_store.items():
                print(f"- {key.replace('_', ' ').title()}: {value}")
        else:
            print("- No vector store metrics")

        print("\nCorpus Profile:")
        if corpus_profile:
            for key, value in corpus_profile.items():
                label = key.replace('_', ' ').title()
                if isinstance(value, dict):
                    print(f"- {label}:")
                    for sub_key, sub_value in value.items():
                        print(f"  - {sub_key}: {sub_value}")
                else:
                    print(f"- {label}: {value}")
        else:
            print("- No corpus profile metrics")

        print("\nCorpus Report:")
        if corpus_report:
            for key, value in corpus_report.items():
                label = key.replace('_', ' ').title()
                if key == "directory_summaries" and isinstance(value, list):
                    print(f"- {label}:")
                    if not value:
                        print("  - None")
                    for summary in value:
                        directory = summary.get("directory", "unknown")
                        print(
                            f"  - {directory}: documents={summary.get('documents_added', 0)}, "
                            f"files_processed={summary.get('files_processed', 0)}, "
                            f"files_skipped={summary.get('files_skipped', 0)}, "
                            f"duration={summary.get('duration_seconds', 0)}s"
                        )
                elif isinstance(value, list):
                    display = ", ".join(str(item) for item in value) if value else "None"
                    print(f"- {label}: {display}")
                else:
                    print(f"- {label}: {value}")
        else:
            print("- No corpus report data")

        print("\nQuery Metrics:")
        if query_metrics:
            for key, value in query_metrics.items():
                print(f"- {key.replace('_', ' ').title()}: {value}")
        else:
            print("- No query metrics recorded")

        print("\nRecent Queries:")
        if recent_queries:
            for entry in recent_queries:
                timestamp = entry.get("timestamp")
                question = entry.get("question")
                latency = entry.get("latency_ms")
                contexts_count = entry.get("contexts")
                strategy = entry.get("strategy")
                print(
                    f"- [{timestamp}] {question} (latency={latency} ms, contexts={contexts_count}, strategy={strategy})"
                )
        else:
            print("- No recent query activity")

        print("\nAlerts:")
        if alerts:
            for alert in alerts:
                print(f"- {alert}")
        else:
            print("- None")

        print("\nConfiguration:")
        for key, value in configuration.items():
            print(f"- {key.replace('_', ' ').title()}: {value}")

    async def show_health_check(self):
        """Display pipeline health diagnostics."""

        if self.pipeline is None:
            raise RuntimeError("Pipeline is not initialized")

        health = await self.pipeline.health_check()
        print("""
🩺 HEALTH CHECK
---------------
""")
        print(f"Overall Status: {health['overall'].title()}")
        print("Components:")
        for component, status in health["components"].items():
            print(f"- {component.title()}: {status}")

    def show_configuration(self):
        """Display raw settings for debugging."""

        print("""
⚙️  CONFIGURATION
----------------
""")
        print(self.config.model_dump_json(indent=2))

    async def run(self):
        """Main entry point for interactive CLI."""

        menu_actions = {
            "1": self.ingest_sample_documents,
            "2": self.query_knowledge_base,
            "3": self.show_system_statistics,
            "4": self.show_health_check,
            "5": self.show_configuration,
            "6": None,
        }

        await self.initialize_system()
        self.print_banner()

        while True:
            choice = self.print_menu()
            if choice == "6":
                print("👋 Exiting demo. Thank you!")
                break

            action = menu_actions.get(choice)
            if action is None:
                print("❌ Invalid selection. Please try again.")
                continue

            if asyncio.iscoroutinefunction(action):
                await action()
            else:
                action()


async def main() -> None:
    """Async entry point."""

    demo = AionDemo()
    await demo.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no cover - manual interruption
        print("\n👋 Demo interrupted by user. Goodbye!")
        LOGGER.info("CLI demo interrupted by user")