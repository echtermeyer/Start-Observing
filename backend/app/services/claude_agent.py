"""
Claude Agent Service for autonomous data analysis and dashboard generation.

This service provides AI-powered capabilities for:
- Analyzing uploaded datasets
- Generating insights and recommendations
- Creating visualizations
- Setting up alerts
- Answering questions about data
"""

import os
import json
import logging
import anthropic
from typing import Any
from datetime import datetime


# ============================================================================
# COLORED LOGGING SETUP
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for LLM logging."""

    # ANSI color codes
    COLORS = {
        'CYAN': '\033[96m',
        'MAGENTA': '\033[95m',
        'YELLOW': '\033[93m',
        'GREEN': '\033[92m',
        'BLUE': '\033[94m',
        'RED': '\033[91m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        'RESET': '\033[0m',
    }

    def format(self, record):
        # Add colors based on log level or custom attributes
        if hasattr(record, 'llm_call'):
            # LLM call start - Cyan
            prefix = f"{self.COLORS['CYAN']}{self.COLORS['BOLD']}🤖 LLM CALL{self.COLORS['RESET']}"
        elif hasattr(record, 'llm_response'):
            # LLM response - Green
            prefix = f"{self.COLORS['GREEN']}{self.COLORS['BOLD']}✅ LLM RESPONSE{self.COLORS['RESET']}"
        elif hasattr(record, 'llm_error'):
            # LLM error - Red
            prefix = f"{self.COLORS['RED']}{self.COLORS['BOLD']}❌ LLM ERROR{self.COLORS['RESET']}"
        elif hasattr(record, 'llm_prompt'):
            # Prompt details - Yellow
            prefix = f"{self.COLORS['YELLOW']}📝 PROMPT{self.COLORS['RESET']}"
        elif hasattr(record, 'llm_output'):
            # Output details - Magenta
            prefix = f"{self.COLORS['MAGENTA']}📤 OUTPUT{self.COLORS['RESET']}"
        else:
            prefix = f"{self.COLORS['BLUE']}ℹ️  INFO{self.COLORS['RESET']}"

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        return f"{self.COLORS['DIM']}[{timestamp}]{self.COLORS['RESET']} {prefix} {record.getMessage()}"


# Create logger for LLM operations
llm_logger = logging.getLogger("llm_agent")
llm_logger.setLevel(logging.DEBUG)

# Remove existing handlers
llm_logger.handlers = []

# Add console handler with colored formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
llm_logger.addHandler(console_handler)

# Prevent propagation to root logger
llm_logger.propagate = False


def log_llm_call(agent_name: str, method: str, context: dict):
    """Log the start of an LLM call."""
    llm_logger.info(
        f"{ColoredFormatter.COLORS['CYAN']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{ColoredFormatter.COLORS['RESET']}"
    )
    record = llm_logger.makeRecord(
        llm_logger.name, logging.INFO, "", 0,
        f"Agent: {agent_name} | Method: {method}", (), None
    )
    record.llm_call = True
    llm_logger.handle(record)

    # Log context summary
    for key, value in context.items():
        if isinstance(value, str) and len(value) > 200:
            value = value[:200] + "..."
        elif isinstance(value, list) and len(value) > 3:
            value = f"[{len(value)} items]"
        llm_logger.info(f"  • {key}: {value}")


def log_llm_prompt(prompt: str, max_length: int = 500):
    """Log the prompt being sent to the LLM."""
    record = llm_logger.makeRecord(
        llm_logger.name, logging.INFO, "", 0,
        f"Sending prompt ({len(prompt)} chars):", (), None
    )
    record.llm_prompt = True
    llm_logger.handle(record)

    # Show truncated prompt
    display_prompt = prompt if len(prompt) <= max_length else prompt[:max_length] + f"\n... [{len(prompt) - max_length} more chars]"
    for line in display_prompt.split('\n')[:15]:  # Show first 15 lines
        llm_logger.info(f"  {ColoredFormatter.COLORS['DIM']}│{ColoredFormatter.COLORS['RESET']} {line}")
    if display_prompt.count('\n') > 15:
        llm_logger.info(f"  {ColoredFormatter.COLORS['DIM']}│ ... [{display_prompt.count(chr(10)) - 15} more lines]{ColoredFormatter.COLORS['RESET']}")


def log_llm_response(response_text: str, tokens_used: dict = None, max_length: int = 800):
    """Log the response from the LLM."""
    record = llm_logger.makeRecord(
        llm_logger.name, logging.INFO, "", 0,
        f"Received response ({len(response_text)} chars):", (), None
    )
    record.llm_response = True
    llm_logger.handle(record)

    if tokens_used:
        llm_logger.info(f"  📊 Tokens - Input: {tokens_used.get('input', '?')}, Output: {tokens_used.get('output', '?')}")

    # Show response
    display_response = response_text if len(response_text) <= max_length else response_text[:max_length] + f"\n... [{len(response_text) - max_length} more chars]"
    for line in display_response.split('\n')[:20]:  # Show first 20 lines
        llm_logger.info(f"  {ColoredFormatter.COLORS['DIM']}│{ColoredFormatter.COLORS['RESET']} {line}")
    if display_response.count('\n') > 20:
        llm_logger.info(f"  {ColoredFormatter.COLORS['DIM']}│ ... [{display_response.count(chr(10)) - 20} more lines]{ColoredFormatter.COLORS['RESET']}")

    llm_logger.info(
        f"{ColoredFormatter.COLORS['GREEN']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{ColoredFormatter.COLORS['RESET']}"
    )


def log_llm_error(error: Exception):
    """Log an LLM error."""
    record = llm_logger.makeRecord(
        llm_logger.name, logging.ERROR, "", 0,
        f"Error: {type(error).__name__}: {str(error)}", (), None
    )
    record.llm_error = True
    llm_logger.handle(record)


def log_parsed_output(output_type: str, data: Any):
    """Log the parsed output from LLM response."""
    record = llm_logger.makeRecord(
        llm_logger.name, logging.INFO, "", 0,
        f"Parsed {output_type}:", (), None
    )
    record.llm_output = True
    llm_logger.handle(record)

    if isinstance(data, list):
        llm_logger.info(f"  📦 List with {len(data)} items")
        for i, item in enumerate(data[:3]):
            if isinstance(item, dict):
                summary = ", ".join(f"{k}={v}" for k, v in list(item.items())[:3])
                llm_logger.info(f"    [{i}] {summary}...")
    elif isinstance(data, dict):
        llm_logger.info(f"  📦 Dict with {len(data)} keys: {list(data.keys())[:5]}")


# ============================================================================
# CLAUDE CLIENT SETUP
# ============================================================================

def get_claude_client() -> anthropic.Anthropic:
    """Get Claude client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    return anthropic.Anthropic(api_key=api_key)


# Model configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


# ============================================================================
# AGENT CLASSES
# ============================================================================

class DataAnalysisAgent:
    """Agent for analyzing datasets and generating insights."""

    def __init__(self):
        self.client = get_claude_client()
        self.agent_name = "DataAnalysisAgent"

    def analyze_dataset(
        self,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict],
        row_count: int
    ) -> dict:
        """
        Perform comprehensive analysis of a dataset.

        Returns structured analysis with:
        - insights: List of findings with severity levels
        - alerts: Recommended alert configurations
        - visualizations: Recommended chart types and configurations
        """
        log_llm_call(self.agent_name, "analyze_dataset", {
            "dataset_name": dataset_name,
            "schema_columns": len(schema),
            "row_count": row_count,
            "sample_data_rows": len(sample_data)
        })

        # Prepare context for Claude
        schema_desc = "\n".join([
            f"  - {col['name']} ({col['type']}): nullable={col.get('nullable', False)}, samples={col.get('sample_values', [])[:3]}"
            for col in schema
        ])

        sample_str = json.dumps(sample_data[:10], indent=2) if sample_data else "No sample data"

        prompt = f"""You are a data analysis expert. Analyze this dataset and provide actionable insights.

DATASET: {dataset_name}
ROW COUNT: {row_count}
COLUMNS: {len(schema)}

SCHEMA:
{schema_desc}

METRICS:
- Total Records: {metrics.get('total_records', 0)}
- Null Rate: {metrics.get('null_rate', 0)}%
- Column Count: {metrics.get('column_count', 0)}
- Average Numeric Value: {metrics.get('avg_value', 'N/A')}
- Anomaly Count: {metrics.get('anomaly_count', 0)}

SAMPLE DATA (first 10 rows):
{sample_str}

Provide your analysis in the following JSON format:
{{
    "summary": "Brief 2-3 sentence summary of the dataset",
    "insights": [
        {{
            "severity": "critical|warning|info",
            "title": "Short title",
            "description": "Detailed description of the finding",
            "affected_columns": ["column1", "column2"],
            "recommendation": "What action to take"
        }}
    ],
    "recommended_alerts": [
        {{
            "type": "threshold|anomaly|trend|missing_data",
            "column": "column_name",
            "condition": "Description of alert condition",
            "threshold": "value if applicable",
            "severity": "critical|warning"
        }}
    ],
    "recommended_visualizations": [
        {{
            "type": "line|bar|scatter|pie|heatmap|histogram",
            "title": "Chart title",
            "description": "What this visualization shows",
            "x_column": "column_name",
            "y_column": "column_name or null",
            "group_by": "column_name or null",
            "rationale": "Why this visualization is useful"
        }}
    ],
    "data_quality_score": 0-100,
    "key_statistics": {{
        "most_complete_column": "column_name",
        "most_variable_column": "column_name",
        "potential_issues": ["issue1", "issue2"]
    }}
}}

Focus on actionable insights. Identify patterns, anomalies, and potential data quality issues.
Return ONLY valid JSON, no other text."""

        log_llm_prompt(prompt)

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
            log_llm_response(response_text, tokens_used)

            # Parse response
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())
                log_parsed_output("analysis", result)
                return result
            except json.JSONDecodeError as e:
                log_llm_error(e)
                return {
                    "summary": "Analysis completed but response parsing failed.",
                    "insights": [],
                    "recommended_alerts": [],
                    "recommended_visualizations": [],
                    "data_quality_score": 50,
                    "key_statistics": {},
                    "raw_response": response_text
                }
        except Exception as e:
            log_llm_error(e)
            raise

    def generate_insights(
        self,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict],
        previous_insights: list[dict] = None
    ) -> list[dict]:
        """Generate specific insights for a dataset."""
        log_llm_call(self.agent_name, "generate_insights", {
            "dataset_name": dataset_name,
            "schema_columns": len(schema),
            "sample_rows": len(sample_data),
            "previous_insights": len(previous_insights) if previous_insights else 0
        })

        schema_desc = "\n".join([
            f"- {col['name']} ({col['type']})"
            for col in schema
        ])

        sample_str = json.dumps(sample_data[:15], indent=2) if sample_data else "No sample data"

        previous_context = ""
        if previous_insights:
            previous_context = f"\nPREVIOUS INSIGHTS (avoid duplicates):\n" + "\n".join([
                f"- {i.get('title')}: {i.get('description')}"
                for i in previous_insights[:5]
            ])

        prompt = f"""Analyze this dataset and generate 3-5 NEW insights.

DATASET: {dataset_name}

SCHEMA:
{schema_desc}

METRICS:
- Records: {metrics.get('total_records', 0)}
- Null Rate: {metrics.get('null_rate', 0)}%
- Anomalies Detected: {metrics.get('anomaly_count', 0)}

SAMPLE DATA:
{sample_str}
{previous_context}

Generate insights in this JSON array format:
[
    {{
        "severity": "critical|warning|info",
        "title": "Concise title (max 50 chars)",
        "description": "Detailed finding with specific numbers and recommendations (2-3 sentences)"
    }}
]

Guidelines:
- critical: Data quality issues, significant anomalies, urgent action needed
- warning: Trends to watch, potential problems, moderate concerns
- info: Interesting patterns, positive trends, general observations

Be specific - reference actual column names and values from the data.
Return ONLY the JSON array, no other text."""

        log_llm_prompt(prompt)

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
            log_llm_response(response_text, tokens_used)

            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                insights = json.loads(response_text.strip())
                if isinstance(insights, list):
                    log_parsed_output("insights", insights)
                    return insights
                return []
            except json.JSONDecodeError as e:
                log_llm_error(e)
                return []
        except Exception as e:
            log_llm_error(e)
            raise


class ChatAgent:
    """Agent for conversational data exploration."""

    def __init__(self):
        self.client = get_claude_client()
        self.agent_name = "ChatAgent"

    def chat(
        self,
        message: str,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict],
        chat_history: list[dict] = None
    ) -> str:
        """
        Have a conversation about the dataset.
        """
        log_llm_call(self.agent_name, "chat", {
            "user_message": message[:100] + "..." if len(message) > 100 else message,
            "dataset_name": dataset_name,
            "history_length": len(chat_history) if chat_history else 0
        })

        schema_desc = "\n".join([
            f"- {col['name']} ({col['type']}): {col.get('sample_values', [])[:2]}"
            for col in schema
        ])

        sample_str = json.dumps(sample_data[:20], indent=2) if sample_data else "No data available"

        # Build conversation history
        messages = []

        # System context as first user message with assistant acknowledgment
        system_context = f"""You are a helpful data analyst assistant. You're helping analyze the "{dataset_name}" dataset.

DATASET CONTEXT:
- Total Records: {metrics.get('total_records', 'Unknown')}
- Null Rate: {metrics.get('null_rate', 0)}%
- Anomalies: {metrics.get('anomaly_count', 0)}

COLUMNS:
{schema_desc}

SAMPLE DATA:
{sample_str}

Guidelines:
- Reference specific columns and values when answering
- If asked about trends or patterns, base answers on the actual data provided
- If you can't answer something from the data, say so clearly
- Be concise but thorough
- When suggesting actions, be specific about what to do

The user will now ask questions about this data."""

        messages.append({"role": "user", "content": system_context})
        messages.append({"role": "assistant", "content": f"I'm ready to help you analyze the {dataset_name} dataset. I can see it has {metrics.get('total_records', 'some')} records across {len(schema)} columns. What would you like to know?"})

        # Add chat history
        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Log the conversation context
        llm_logger.info(f"  💬 Conversation has {len(messages)} messages")
        log_llm_prompt(f"User question: {message}\n\nWith context: {len(schema)} columns, {len(sample_data)} sample rows")

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1024,
                messages=messages
            )

            response_text = response.content[0].text
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
            log_llm_response(response_text, tokens_used)

            return response_text
        except Exception as e:
            log_llm_error(e)
            raise


class VisualizationAgent:
    """Agent for generating appropriate visualizations."""

    def __init__(self):
        self.client = get_claude_client()
        self.agent_name = "VisualizationAgent"

    def generate_visualizations(
        self,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict]
    ) -> list[dict]:
        """
        Generate Vega-Lite visualization specifications based on data analysis.
        """
        log_llm_call(self.agent_name, "generate_visualizations", {
            "dataset_name": dataset_name,
            "schema_columns": len(schema),
            "sample_rows": len(sample_data)
        })

        schema_desc = "\n".join([
            f"- {col['name']} (type: {col['type']}, nullable: {col.get('nullable', False)})"
            for col in schema
        ])

        sample_str = json.dumps(sample_data[:30], indent=2) if sample_data else "[]"

        prompt = f"""You are a data visualization expert. Analyze this dataset and create 4-5 Vega-Lite visualization specifications.

DATASET: {dataset_name}
RECORDS: {metrics.get('total_records', 0)}

SCHEMA:
{schema_desc}

SAMPLE DATA:
{sample_str}

Create visualizations that reveal insights from this specific data. Return a JSON array of visualization objects:

[
    {{
        "id": "unique-id",
        "title": "Descriptive Title",
        "description": "What this chart shows and why it's useful",
        "spec": {{
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {{"values": []}},
            "mark": "...",
            "encoding": {{...}}
        }}
    }}
]

IMPORTANT RULES:
1. The "data" field MUST be {{"values": []}} - actual data will be injected later
2. Use only columns that exist in the schema
3. Choose appropriate chart types for the data types:
   - Time/date columns: line charts, area charts
   - Categories/strings: bar charts, pie charts
   - Numbers: histograms, scatter plots
   - Two numeric columns: scatter plots with correlation
4. Include proper axis labels and tooltips
5. Use a consistent color scheme: ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#6b7280"]

Return ONLY valid JSON array, no other text."""

        log_llm_prompt(prompt)

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
            log_llm_response(response_text, tokens_used)

            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                visualizations = json.loads(response_text.strip())
                log_parsed_output("visualizations", visualizations)

                # Inject actual data into specs
                for viz in visualizations:
                    if "spec" in viz and "data" in viz["spec"]:
                        viz["spec"]["data"]["values"] = sample_data[:100]

                return visualizations
            except json.JSONDecodeError as e:
                log_llm_error(e)
                return []
        except Exception as e:
            log_llm_error(e)
            raise


class AlertAgent:
    """Agent for intelligent alert configuration and monitoring."""

    def __init__(self):
        self.client = get_claude_client()
        self.agent_name = "AlertAgent"

    def analyze_for_alerts(
        self,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict],
        existing_alerts: list[dict] = None
    ) -> dict:
        """
        Analyze dataset and recommend alert configurations.
        """
        log_llm_call(self.agent_name, "analyze_for_alerts", {
            "dataset_name": dataset_name,
            "schema_columns": len(schema),
            "sample_rows": len(sample_data),
            "existing_alerts": len(existing_alerts) if existing_alerts else 0
        })

        schema_desc = "\n".join([
            f"- {col['name']} ({col['type']})"
            for col in schema
        ])

        sample_str = json.dumps(sample_data[:20], indent=2) if sample_data else "[]"

        existing_context = ""
        if existing_alerts:
            existing_context = "\nEXISTING ALERTS (avoid duplicates):\n" + "\n".join([
                f"- {a.get('title')}: {a.get('type')}"
                for a in existing_alerts[:5]
            ])

        prompt = f"""Analyze this dataset for monitoring and alerting needs.

DATASET: {dataset_name}

SCHEMA:
{schema_desc}

METRICS:
- Records: {metrics.get('total_records', 0)}
- Null Rate: {metrics.get('null_rate', 0)}%
- Anomalies: {metrics.get('anomaly_count', 0)}

SAMPLE DATA:
{sample_str}
{existing_context}

Provide alert recommendations in this JSON format:
{{
    "recommended_configs": [
        {{
            "alert_type": "threshold|anomaly|trend|missing_data|data_quality",
            "column": "column_name or null for dataset-level",
            "condition": "Human readable condition",
            "threshold_value": "numeric value or null",
            "severity": "critical|warning",
            "rationale": "Why this alert is important"
        }}
    ],
    "immediate_alerts": [
        {{
            "severity": "critical|warning",
            "type": "threshold|anomaly|data_quality",
            "title": "Alert title",
            "message": "Detailed alert message with specific values"
        }}
    ],
    "monitoring_summary": "Brief summary of data health and what to watch"
}}

Guidelines:
- Recommend 2-4 alert configurations based on the data characteristics
- Only create immediate alerts if there are actual issues visible in the data
- Be specific about threshold values based on the actual data ranges
- Focus on actionable alerts, not noise

Return ONLY valid JSON, no other text."""

        log_llm_prompt(prompt)

        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            tokens_used = {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
            log_llm_response(response_text, tokens_used)

            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())
                log_parsed_output("alert_analysis", result)
                return result
            except json.JSONDecodeError as e:
                log_llm_error(e)
                return {
                    "recommended_configs": [],
                    "immediate_alerts": [],
                    "monitoring_summary": "Analysis completed but response parsing failed."
                }
        except Exception as e:
            log_llm_error(e)
            raise


class DatasetPipelineAgent:
    """
    Orchestrator agent that coordinates the full analysis pipeline.
    """

    def __init__(self):
        self.analysis_agent = DataAnalysisAgent()
        self.insight_agent = DataAnalysisAgent()
        self.viz_agent = VisualizationAgent()
        self.alert_agent = AlertAgent()
        self.agent_name = "DatasetPipelineAgent"

    def run_full_pipeline(
        self,
        dataset_id: str,
        dataset_name: str,
        schema: list[dict],
        metrics: dict,
        sample_data: list[dict],
        row_count: int,
        user_id: str
    ) -> dict:
        """
        Run the complete analysis pipeline for a new dataset.
        """
        llm_logger.info(
            f"\n{ColoredFormatter.COLORS['BOLD']}{ColoredFormatter.COLORS['BLUE']}"
            f"🚀 STARTING FULL ANALYSIS PIPELINE FOR: {dataset_name}"
            f"{ColoredFormatter.COLORS['RESET']}\n"
        )

        results = {
            "dataset_id": dataset_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": None,
            "insights": [],
            "visualizations": [],
            "alerts": None,
            "errors": []
        }

        # Step 1: Full dataset analysis
        llm_logger.info(f"{ColoredFormatter.COLORS['YELLOW']}📊 Step 1/4: Dataset Analysis{ColoredFormatter.COLORS['RESET']}")
        try:
            results["analysis"] = self.analysis_agent.analyze_dataset(
                dataset_name=dataset_name,
                schema=schema,
                metrics=metrics,
                sample_data=sample_data,
                row_count=row_count
            )
        except Exception as e:
            log_llm_error(e)
            results["errors"].append(f"Analysis failed: {str(e)}")

        # Step 2: Generate insights
        llm_logger.info(f"{ColoredFormatter.COLORS['YELLOW']}💡 Step 2/4: Insight Generation{ColoredFormatter.COLORS['RESET']}")
        try:
            results["insights"] = self.insight_agent.generate_insights(
                dataset_name=dataset_name,
                schema=schema,
                metrics=metrics,
                sample_data=sample_data
            )
        except Exception as e:
            log_llm_error(e)
            results["errors"].append(f"Insight generation failed: {str(e)}")

        # Step 3: Generate visualizations
        llm_logger.info(f"{ColoredFormatter.COLORS['YELLOW']}📈 Step 3/4: Visualization Generation{ColoredFormatter.COLORS['RESET']}")
        try:
            results["visualizations"] = self.viz_agent.generate_visualizations(
                dataset_name=dataset_name,
                schema=schema,
                metrics=metrics,
                sample_data=sample_data
            )
        except Exception as e:
            log_llm_error(e)
            results["errors"].append(f"Visualization generation failed: {str(e)}")

        # Step 4: Alert analysis
        llm_logger.info(f"{ColoredFormatter.COLORS['YELLOW']}🚨 Step 4/4: Alert Analysis{ColoredFormatter.COLORS['RESET']}")
        try:
            results["alerts"] = self.alert_agent.analyze_for_alerts(
                dataset_name=dataset_name,
                schema=schema,
                metrics=metrics,
                sample_data=sample_data
            )
        except Exception as e:
            log_llm_error(e)
            results["errors"].append(f"Alert analysis failed: {str(e)}")

        llm_logger.info(
            f"\n{ColoredFormatter.COLORS['BOLD']}{ColoredFormatter.COLORS['GREEN']}"
            f"✅ PIPELINE COMPLETE FOR: {dataset_name}"
            f"{ColoredFormatter.COLORS['RESET']}"
            f"\n   Insights: {len(results['insights'])}, Visualizations: {len(results['visualizations'])}, Errors: {len(results['errors'])}\n"
        )

        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def analyze_dataset(dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict], row_count: int) -> dict:
    """Quick function to analyze a dataset."""
    agent = DataAnalysisAgent()
    return agent.analyze_dataset(dataset_name, schema, metrics, sample_data, row_count)


def generate_insights(dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict], previous_insights: list[dict] = None) -> list[dict]:
    """Quick function to generate insights."""
    agent = DataAnalysisAgent()
    return agent.generate_insights(dataset_name, schema, metrics, sample_data, previous_insights)


def chat_about_data(message: str, dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict], history: list[dict] = None) -> str:
    """Quick function for chat responses."""
    agent = ChatAgent()
    return agent.chat(message, dataset_name, schema, metrics, sample_data, history)


def generate_visualizations(dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict]) -> list[dict]:
    """Quick function to generate visualizations."""
    agent = VisualizationAgent()
    return agent.generate_visualizations(dataset_name, schema, metrics, sample_data)


def analyze_for_alerts(dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict], existing_alerts: list[dict] = None) -> dict:
    """Quick function to analyze for alerts."""
    agent = AlertAgent()
    return agent.analyze_for_alerts(dataset_name, schema, metrics, sample_data, existing_alerts)


def run_pipeline(dataset_id: str, dataset_name: str, schema: list[dict], metrics: dict, sample_data: list[dict], row_count: int, user_id: str) -> dict:
    """Quick function to run the full pipeline."""
    agent = DatasetPipelineAgent()
    return agent.run_full_pipeline(dataset_id, dataset_name, schema, metrics, sample_data, row_count, user_id)
