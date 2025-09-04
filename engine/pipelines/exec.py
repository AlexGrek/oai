import logging
from engine.apiclient import BackendAPIClient
from engine.model_picker import ModelPicker
from engine.pipelines.models import *
from engine.pipelines.query_send import QuerySender

logger = logging.getLogger(__name__)

class PipelineExecutor:
    """
    Executes a defined pipeline asynchronously, managing state,
    conditions, and data extraction.
    """

    def __init__(
        self, pipeline: Pipeline, query_sender: QuerySender, client: BackendAPIClient
    ):
        self.pipeline = pipeline
        self.query_sender = query_sender
        self.client = client
        self.context: Dict[str, Any] = {}

    async def execute(self, initial_input: Any) -> Dict[str, Any]:
        """
        Runs the entire pipeline with a given initial input.
        """
        self.context = {"input": initial_input}
        logging.debug(
            f"🚀 Starting pipeline '{self.pipeline.name}' with input: {initial_input}\n"
        )

        for i, step in enumerate(self.pipeline.steps):
            logging.debug(f"--- Step {i+1}: Action '{step.action}' ---")

            should_run = await self._evaluate_conditions(step.if_condition)
            if not should_run:
                logging.debug("Skipped due to 'if' condition not being met.\n")
                continue

            if step.action == "query":
                await self._execute_query_step(step)
            else:
                logging.debug(f"⚠️ Unknown action: {step.action}")

            logging.debug("Step finished.\n")

        logging.debug("✅ Pipeline execution complete.")
        return self.context

    async def _execute_query_step(self, step: Step):
        if not step.message:
            return

        # 1. Substitute variables in prompts
        system_prompt = self._substitute_variables(step.message.system)
        user_prompt = self._substitute_variables(step.message.user)

        # 2. Perform the LLM query (mocked for this example)
        json_flag = step.json if step.json else False
        model = step.model if step.model else ""
        response = await self._perform_llm_query(
            model, step, system_prompt, user_prompt
        )

        # 3. Extract data from the response
        if step.extract:
            self._extract_data(response["message"]["content"], step.extract, json_flag)

    def _substitute_variables(self, template: str) -> str:
        """Replaces ${variable.path} with values from the context."""

        def replace_match(match):
            path = match.group(1)
            value = self._lookup_path(self.context, path)
            return str(value) if value is not None else ""

        return re.sub(r"\$\{([^}]+)\}", replace_match, template)

    def _lookup_path(self, data: Dict[str, Any], path: str) -> Any:
        """Accesses a nested value in a dict using dot notation."""
        keys = path.split(".")
        current_val = data
        for key in keys:
            if isinstance(current_val, dict) and key in current_val:
                current_val = current_val[key]
            else:
                return None
        return current_val

    def _extract_data(
        self, response: str, rules: List[ExtractRule], is_json_response: bool
    ):
        """Processes extraction rules and updates the context."""
        data_to_parse = None
        if is_json_response:
            try:
                data_to_parse = json.loads(response)
            except json.JSONDecodeError:
                logging.debug(f"⚠️ Failed to parse JSON response: {response}")
                return

        for rule in rules:
            value = None
            if rule.fulltext:
                value = response
            elif rule.jq and data_to_parse is not None:
                # Basic jq-like functionality
                if rule.jq == ".":
                    value = data_to_parse
                else:
                    path = rule.jq.strip(".")
                    value = self._lookup_path(data_to_parse, path)

            if value is not None:
                value = self._cast_type(value, rule.type)
                self.context[rule.name] = value

    def _cast_type(self, value: Any, target_type: Optional[str]) -> Any:
        """Casts a value to the specified type."""
        if target_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        if target_type == "boolean":
            return str(value).lower() in ["true", "1", "yes"]
        return value

    async def _evaluate_conditions(self, conditions: Optional[List[Condition]]) -> bool:
        if not conditions:
            return True  # No conditions means the step should always run

        # Using asyncio.gather to evaluate all root conditions concurrently
        results = await asyncio.gather(
            *[self._evaluate_single_condition(c) for c in conditions]
        )
        return all(results)

    async def _evaluate_single_condition(self, condition: Condition) -> bool:
        """Recursively evaluates a single condition and its nested 'and'/'or' clauses."""
        val_a = self._lookup_path(self.context, condition.a)
        val_b = condition.b

        ops = {
            "gt": lambda a, b: a > b,
            "lt": lambda a, b: a < b,
            "eq": lambda a, b: a == b,
            "is": lambda a, b: a is b,
            "is_not": lambda a, b: a is not b,
            "contains": lambda a, b: b in a,
        }

        op_func = ops.get(condition.op)
        if val_a is None or not op_func:
            result = False
        else:
            # Try to compare types directly, but fall back to string comparison
            try:
                result = op_func(val_a, val_b)
            except TypeError:
                result = op_func(str(val_a), str(val_b))

        # Handle nested conditions
        if result and condition.and_:
            and_results = await asyncio.gather(
                *[self._evaluate_single_condition(c) for c in condition.and_]
            )
            return all(and_results)

        if not result and condition.or_:
            or_results = await asyncio.gather(
                *[self._evaluate_single_condition(c) for c in condition.or_]
            )
            return any(or_results)

        return result

    async def _perform_llm_query(
        self, model: str, payload: Step, system: str, user: str
    ) -> Dict[str, Any]:
        """
        IMPLEMENTATION of an LLM call.
        Replace this with your actual LLM client (e.g., OpenAI, Anthropic).
        """

        response = await self.query_sender.execute(
            payload.lang, model, payload.json, system, user
        )
        return response
