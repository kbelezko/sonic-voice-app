"""AWS Bedrock integration for conversational AI"""

import json
import boto3
from typing import List, Dict, Any, Optional, AsyncIterator
from botocore.config import Config
from botocore.exceptions import ClientError
import time
import logging
import traceback

logger = logging.getLogger(__name__)

class BedrockService:
    """Service for AWS Bedrock Claude integration"""
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "us.anthropic.claude-3-5-sonnet-20250122-v1:0"
    ):
        # Configure with retry logic
        config = Config(
            region_name=region_name,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            config=config
        )
        self.model_id = model_id
        self.max_tokens = 4096
    
    def create_system_prompt(self) -> str:
        """Create system prompt for hotel booking assistant"""
        return """You are a helpful hotel booking assistant. Help users find and book hotels through conversation. 

Your responsibilities:
- Ask clarifying questions when needed (dates, location, number of guests)
- Use the search_hotels tool to find available hotels
- Use get_hotel_details to show detailed information about specific hotels
- Use create_booking to complete reservations once you have all required information
- Use get_booking to retrieve existing booking details
- Use cancel_booking to cancel reservations

Be conversational, friendly, and guide users through the booking process step by step. Always confirm important details before creating a booking."""
    
    def format_conversation_history(
        self,
        messages: List[Dict[str, str]],
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """Format conversation history for Claude API (last N messages)"""
        # Take only the last N messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        formatted = []
        for msg in recent_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Claude API uses "user" and "assistant" roles
            if role in ["user", "assistant"]:
                formatted.append({
                    "role": role,
                    "content": content
                })
        
        return formatted
    
    def format_tools_for_claude(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format MCP tools for Claude's tool use format"""
        return tools
    
    def invoke_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke Claude with tool definitions"""
        try:
            formatted_messages = self.format_conversation_history(messages)
            formatted_tools = self.format_tools_for_claude(tools)
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": formatted_messages,
                "tools": formatted_tools
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            logger.info(f"Invoking Bedrock model: {self.model_id}")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS ClientError - Code: {error_code}, Message: {error_message}")
            logger.error(f"Model ID used: {self.model_id}")
            logger.error(f"Full error response: {json.dumps(e.response, indent=2)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            if error_code == 'ThrottlingException':
                # Exponential backoff
                logger.warning("Throttled, retrying in 2 seconds...")
                time.sleep(2)
                return self.invoke_with_tools(messages, tools, system_prompt)
            elif error_code == 'AccessDeniedException':
                return {
                    "error": "Access denied to AWS Bedrock. Check credentials and permissions."
                }
            else:
                return {"error": f"AWS Bedrock error: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Unexpected error in invoke_with_tools: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {"error": f"Bedrock invocation failed: {str(e)}"}
    
    async def invoke_with_tools_streaming(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Invoke Claude with streaming response"""
        try:
            formatted_messages = self.format_conversation_history(messages)
            formatted_tools = self.format_tools_for_claude(tools)
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": formatted_messages,
                "tools": formatted_tools
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            response = self.bedrock_runtime.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Process streaming response
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())
                        yield chunk_data
        
        except Exception as e:
            yield {"error": f"Streaming failed: {str(e)}"}
    
    def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from Claude response"""
        tool_calls = []
        content = response.get("content", [])
        
        for block in content:
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {})
                })
        
        return tool_calls
    
    def extract_text_response(self, response: Dict[str, Any]) -> str:
        """Extract text content from Claude response"""
        text_parts = []
        content = response.get("content", [])
        
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        return " ".join(text_parts)
    
    def format_tool_result(
        self,
        tool_use_id: str,
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format tool execution result for injection back into conversation"""
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(tool_result)
                }
            ]
        }
