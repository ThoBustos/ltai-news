"""Centralized Opik management for all agents and workflows."""

import opik
from opik.integrations.langchain import track_langgraph, OpikTracer
from typing import Optional, List

from app.core.logging import logger
from app.config.settings import settings


class OpikManager:
    """Centralized Opik management for all agents and workflows."""
    
    def __init__(self):
        """Initialize Opik configuration."""
        self.enabled = False
        self.configured = False
        
        if settings.opik_api_key:
            try:
                opik.configure(
                    api_key=settings.opik_api_key,
                    workspace=settings.opik_workspace
                )
                self.enabled = True
                self.configured = True
                logger.info(f"Opik configured successfully for project: {settings.opik_project_name or 'ltai-news'}")
            except Exception as e:
                logger.error(f"Failed to configure Opik: {e}")
                self.enabled = False
        else:
            logger.warning("Opik API key not found - tracing disabled")
    
    def create_tracer(self, workflow_name: str, tags: Optional[List[str]] = None) -> Optional[OpikTracer]:
        """Create workflow-specific tracer with consistent project settings.
        
        Args:
            workflow_name: Name of the workflow being traced
            tags: Optional list of tags for the tracer
            
        Returns:
            OpikTracer instance if Opik is enabled, None otherwise
        """
        if not self.enabled:
            return None
            
        try:
            return OpikTracer(
                project_name=settings.opik_project_name or "ltai-news",
                tags=(tags or []) + [workflow_name, "production"],
                metadata={
                    "workflow": workflow_name,
                    "version": "1.0",
                    "environment": "production"
                }
            )
        except Exception as e:
            logger.error(f"Failed to create Opik tracer for {workflow_name}: {e}")
            return None
    
    def track_workflow(self, compiled_graph, workflow_name: str, tags: Optional[List[str]] = None):
        """Wrap LangGraph with Opik tracking.
        
        Args:
            compiled_graph: Compiled LangGraph workflow
            workflow_name: Name of the workflow
            tags: Optional list of tags
            
        Returns:
            Tracked workflow if Opik is enabled, original workflow otherwise
        """
        if not self.enabled:
            logger.debug(f"Opik tracking disabled for workflow {workflow_name}")
            return compiled_graph
            
        try:
            tracer = self.create_tracer(workflow_name, tags)
            if tracer:
                tracked = track_langgraph(compiled_graph, tracer)
                logger.debug(f"Opik tracking enabled for workflow {workflow_name}")
                return tracked
            else:
                logger.warning(f"Failed to create tracer for {workflow_name}, returning untracked workflow")
                return compiled_graph
        except Exception as e:
            logger.error(f"Failed to track workflow {workflow_name} with Opik: {e}")
            return compiled_graph
    
    def get_status(self) -> dict:
        """Get current Opik manager status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "project_name": settings.opik_project_name or "ltai-news",
            "workspace": settings.opik_workspace,
            "has_api_key": bool(settings.opik_api_key)
        }


# Global instance
opik_manager = OpikManager()