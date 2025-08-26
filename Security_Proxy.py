import re
import json
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailSecurityProxy")

class IntentType(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UNKNOWN = "unknown"

class SecurityProxy:
    """
    Email Agent Security Proxy for defending against EAH attacks.
    This MCP can be embedded into LLMs to validate actions against user intent.
    """
    
    def __init__(self):
        # Initialize patterns for intent extraction
        self.read_patterns = [
            r"read.*email",
            r"show.*email",
            r"check.*email",
            r"view.*email",
            r"open.*email",
            r"see.*email",
            r"display.*email",
            r"look.*at.*email",
            r"what.*email",
            r"fetch.*email"
        ]
        
        self.write_patterns = [
            r"send.*email",
            r"write.*email",
            r"compose.*email",
            r"reply.*email",
            r"forward.*email",
            r"create.*email",
            r"draft.*email"
        ]
        
        self.delete_patterns = [
            r"delete.*email",
            r"remove.*email",
            r"trash.*email",
            r"discard.*email",
            r"erase.*email"
        ]
        
        # Compile regex patterns
        self.read_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.read_patterns]
        self.write_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.write_patterns]
        self.delete_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.delete_patterns]
        
        logger.info("Email Security Proxy initialized")
    
    def extract_intent(self, user_prompt: str) -> Tuple[IntentType, Dict[str, Any]]:
        """
        Extract the user's intent from the prompt.
        Returns the intent type and extracted parameters.
        """
        # Check for read intent
        for pattern in self.read_regex:
            if pattern.search(user_prompt):
                # Extract email parameters (from, subject, etc.)
                from_match = re.search(r"from[:\s]*([^\s,]+@[^\s,]+)", user_prompt, re.IGNORECASE)
                subject_match = re.search(r"subject[:\s]*['\"]([^'\"]+)['\"]", user_prompt, re.IGNORECASE)
                
                params = {}
                if from_match:
                    params["from"] = from_match.group(1).strip()
                if subject_match:
                    params["subject"] = subject_match.group(1).strip()
                    
                return IntentType.READ, params
        
        # Check for write intent
        for pattern in self.write_regex:
            if pattern.search(user_prompt):
                # Extract email parameters (to, subject, body, etc.)
                to_match = re.search(r"to[:\s]*([^\s,]+@[^\s,]+)", user_prompt, re.IGNORECASE)
                subject_match = re.search(r"subject[:\s]*['\"]([^'\"]+)['\"]", user_prompt, re.IGNORECASE)
                
                params = {}
                if to_match:
                    params["to"] = to_match.group(1).strip()
                if subject_match:
                    params["subject"] = subject_match.group(1).strip()
                    
                return IntentType.WRITE, params
        
        # Check for delete intent
        for pattern in self.delete_regex:
            if pattern.search(user_prompt):
                # Extract email parameters (from, subject, etc.)
                from_match = re.search(r"from[:\s]*([^\s,]+@[^\s,]+)", user_prompt, re.IGNORECASE)
                subject_match = re.search(r"subject[:\s]*['\"]([^'\"]+)['\"]", user_prompt, re.IGNORECASE)
                
                params = {}
                if from_match:
                    params["from"] = from_match.group(1).strip()
                if subject_match:
                    params["subject"] = subject_match.group(1).strip()
                    
                return IntentType.DELETE, params
        
        # Default to unknown intent
        return IntentType.UNKNOWN, {}
    
    def validate_action(self, user_prompt: str, proposed_action: str, 
                       action_params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate if the proposed action aligns with the user's intent.
        Returns (is_valid, reason)
        """
        # Extract user intent
        user_intent, user_params = self.extract_intent(user_prompt)
        
        # Extract proposed action type
        proposed_action_type = self._get_action_type(proposed_action)
        
        # Check intent alignment
        if user_intent != proposed_action_type:
            return False, f"Intent mismatch: User intended {user_intent.value} but action is {proposed_action_type.value}"
        
        # Check parameter consistency based on intent
        if user_intent == IntentType.READ:
            return self._validate_read_params(user_params, action_params)
        elif user_intent == IntentType.WRITE:
            return self._validate_write_params(user_params, action_params)
        elif user_intent == IntentType.DELETE:
            return self._validate_delete_params(user_params, action_params)
        
        # Unknown intent - be conservative and reject
        return False, "Unknown user intent"
    
    def _get_action_type(self, action: str) -> IntentType:
        """Determine the type of action from the action string."""
        action_lower = action.lower()
        
        if any(read_action in action_lower for read_action in ["read", "fetch", "get", "retrieve"]):
            return IntentType.READ
        elif any(write_action in action_lower for write_action in ["send", "write", "compose", "reply", "forward"]):
            return IntentType.WRITE
        elif any(delete_action in action_lower for delete_action in ["delete", "remove", "trash"]):
            return IntentType.DELETE
        
        return IntentType.UNKNOWN
    
    def _validate_read_params(self, user_params: Dict[str, Any], 
                            action_params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate parameters for read actions."""
        # Check if 'from' parameter matches
        if "from" in user_params and "from" in action_params:
            if user_params["from"] != action_params["from"]:
                return False, f"From address mismatch: User specified {user_params['from']} but action uses {action_params['from']}"
        
        # Check if 'subject' parameter matches
        if "subject" in user_params and "subject" in action_params:
            if user_params["subject"].lower() != action_params["subject"].lower():
                return False, f"Subject mismatch: User specified '{user_params['subject']}' but action uses '{action_params['subject']}'"
        
        return True, "Parameters validated successfully"
    
    def _validate_write_params(self, user_params: Dict[str, Any], 
                             action_params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate parameters for write actions."""
        # Check if 'to' parameter matches
        if "to" in user_params and "to" in action_params:
            if user_params["to"] != action_params["to"]:
                return False, f"To address mismatch: User specified {user_params['to']} but action uses {action_params['to']}"
        
        # Check if 'subject' parameter matches (if specified by user)
        if "subject" in user_params and "subject" in action_params:
            if user_params["subject"].lower() != action_params["subject"].lower():
                return False, f"Subject mismatch: User specified '{user_params['subject']}' but action uses '{action_params['subject']}'"
        
        return True, "Parameters validated successfully"
    
    def _validate_delete_params(self, user_params: Dict[str, Any], 
                              action_params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate parameters for delete actions."""
        # Similar to read validation
        return self._validate_read_params(user_params, action_params)
    
    def validate_response_content(self, email_content: str, proposed_response: str) -> Tuple[bool, str]:
        """
        Validate that the proposed response is consistent with the actual email content.
        This helps prevent deceptive output attacks.
        """
        # Simple check: if the response is significantly longer than the email content
        # it might contain additional malicious instructions
        if len(proposed_response) > len(email_content) * 1.5:
            return False, "Response is significantly longer than email content, potential deceptive output"
        
        # Check for common attack indicators in the response
        attack_indicators = [
            "forward this email",
            "click this link",
            "download this attachment",
            "reply with your password",
            "provide your credentials",
            "execute this code",
            "run this command",
            "ignore security warnings"
        ]
        
        proposed_lower = proposed_response.lower()
        for indicator in attack_indicators:
            if indicator in proposed_lower:
                return False, f"Response contains potential attack indicator: '{indicator}'"
        
        # Check if the response accurately represents the email content
        # This is a simplified check - in a real implementation, you might use
        # more advanced NLP techniques to compare semantic similarity
        email_keywords = set(email_content.lower().split())
        response_keywords = set(proposed_response.lower().split())
        
        # If the response introduces many new keywords not in the email
        new_keywords = response_keywords - email_keywords
        if len(new_keywords) > len(response_keywords) * 0.3:  # 30% new keywords
            return False, "Response introduces many new concepts not present in the email"
        
        return True, "Response content validated successfully"
    
    def process_request(self, user_prompt: str, proposed_action: str, 
                       action_params: Dict[str, Any], email_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method to process a request through the security proxy.
        Returns a decision with validation results.
        """
        logger.info(f"Processing request: User prompt='{user_prompt}', Action='{proposed_action}'")
        
        # Validate the action against user intent
        is_valid, reason = self.validate_action(user_prompt, proposed_action, action_params)
        
        result = {
            "action_approved": is_valid,
            "validation_reason": reason,
            "user_intent": self.extract_intent(user_prompt)[0].value
        }
        
        # For read actions, also validate the response content if available
        if is_valid and email_content and self._get_action_type(proposed_action) == IntentType.READ:
            # In a real implementation, we would have the proposed response here
            # For demonstration, we'll simulate this check
            response_valid, response_reason = self.validate_response_content(email_content, "Simulated response based on email content")
            if not response_valid:
                result["action_approved"] = False
                result["validation_reason"] = f"Action approved but response validation failed: {response_reason}"
        
        logger.info(f"Request processed: Approved={result['action_approved']}, Reason={result['validation_reason']}")
        return result


# Example usage and integration
if __name__ == "__main__":
    # Initialize the security proxy
    security_proxy = SecurityProxy()
    
    # Example 1: Valid read request
    user_prompt = "Read the latest email from john@example.com"
    proposed_action = "read_email"
    action_params = {"from": "john@example.com", "limit": 1}
    
    result = security_proxy.process_request(user_prompt, proposed_action, action_params)
    print("Example 1 - Valid read request:")
    print(json.dumps(result, indent=2))
    print()
    
    # Example 2: Hijacked write request (EAH attack)
    user_prompt = "Read the latest email from john@example.com"
    proposed_action = "write_email"
    action_params = {"to": "attacker@evil.com", "subject": "Sensitive data", "body": "Here is the data you requested"}
    
    result = security_proxy.process_request(user_prompt, proposed_action, action_params)
    print("Example 2 - Hijacked write request (EAH attack):")
    print(json.dumps(result, indent=2))
    print()
    
    # Example 3: Parameter mismatch attack
    user_prompt = "Read emails from john@example.com with subject 'Project Update'"
    proposed_action = "read_email"
    action_params = {"from": "attacker@evil.com", "subject": "Project Update"}
    
    result = security_proxy.process_request(user_prompt, proposed_action, action_params)
    print("Example 3 - Parameter mismatch attack:")
    print(json.dumps(result, indent=2))