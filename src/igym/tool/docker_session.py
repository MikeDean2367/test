import docker
from typing import Dict, Any, Optional
from .base import BaseSession
from .type import (
    ToolExecutionResult, 
    ToolExecutionStatus, 
    iGymToolExecutionException
)

class DockerSession(BaseSession):
    """Session running in a Docker container"""
    
    def __init__(
        self,
        image: str,
        docker_host: str = None,
        auto_remove: bool = True,
        **container_kwargs
    ):
        """
        Initialize Docker session
        
        Args:
            image: Docker image to use
            docker_host: Docker host URL
            auto_remove: Whether to auto-remove container
            container_kwargs: Additional container parameters
        """
        super().__init__(config={
            "image": image,
            "auto_remove": auto_remove,
            **container_kwargs
        })
        
        self.image = image
        self.auto_remove = auto_remove
        self.container_kwargs = container_kwargs
        self.container = None
        self.client = docker.DockerClient(base_url=docker_host) if docker_host else docker.from_env()
    
    def start(self) -> None:
        """Start the Docker container"""
        if self.container is None:
            self.container = self.client.containers.run(
                self.image,
                detach=True,
                auto_remove=self.auto_remove,
                **self.container_kwargs
            )
            super().start()
    
    def stop(self) -> None:
        """Stop the Docker container"""
        if self.container:
            self.container.stop()
            self.container = None
            super().stop()
    
    def execute(self, command: str, **exec_kwargs) -> ToolExecutionResult:
        """
        Execute a command in the Docker container
        
        Args:
            command: Command to execute
            exec_kwargs: Additional exec parameters
            
        Returns:
            ToolResult with execution output
        """
        if not self.is_active():
            self.start()
            
        try:
            exec_result = self.container.exec_run(command, **exec_kwargs)
            return ToolExecutionResult(
                status=ToolExecutionStatus.COMPLETED,
                output={
                    'exit_code': exec_result.exit_code,
                    'output': exec_result.output.decode('utf-8')
                }
            )
        except Exception as e:
            raise iGymToolExecutionException(
                tool_name="docker_exec",
                error=f"Docker command execution failed: {str(e)}"
            )
    
    def save(self) -> Dict[str, Any]:
        """Save Docker session state"""
        state = super().save()
        state.update({
            "container_id": self.container.id if self.container else None,
            "image": self.image,
            "auto_remove": self.auto_remove
        })
        return state
    
    def load(self, state: Dict[str, Any]) -> None:
        """Load Docker session state"""
        super().load(state)
        if state.get("container_id"):
            try:
                self.container = self.client.containers.get(state["container_id"])
            except docker.errors.NotFound:
                self.container = None