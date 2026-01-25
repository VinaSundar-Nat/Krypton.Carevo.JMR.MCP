import uvicorn
from config import config
from mcp.server.fastmcp import FastMCP
from services.health_check_service import health_mcp
from services.job_management_service import job_listing_mcp, setup_joblisting_server
from services.application_service import applications_mcp, setup_user_application_server
import contextlib
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware

from utility import logprovider

logger = logprovider.get_logger()

healthsvc = health_mcp
jobsvc = job_listing_mcp
appsvc = applications_mcp


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        setup_joblisting_server(jobsvc)
        setup_user_application_server(appsvc)
        await stack.enter_async_context(healthsvc.session_manager.run())
        await stack.enter_async_context(jobsvc.session_manager.run())
        await stack.enter_async_context(appsvc.session_manager.run())
        yield

def serverOps() -> Starlette:
    origins = config['ORIGINS']
    logger.info(f"Registering MCP streamable HTTP transport..")
    host = config['API_ENDPOINT']

    app = Starlette(
        routes=[
            Mount("/app", healthsvc.streamable_http_app()),
            Mount("/job-listing", jobsvc.streamable_http_app()),
            Mount("/user-application", appsvc.streamable_http_app()),
        ],
        lifespan=lifespan,        
    )

    app = CORSMiddleware(
        app,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PUT"],  # MCP streamable HTTP methods
        expose_headers=["Mcp-Session-Id", "X-Request-Id"]
    )

    return app


if __name__ == "__main__":
    logger.info(f"Registering MCP streamable HTTP transport..")
    app =  serverOps()
    uvicorn.run(app, host="127.0.0.1", port=8445)
    logger.info(f"Registered MCP services..")
