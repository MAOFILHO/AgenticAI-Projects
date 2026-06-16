"""
AgentCore Customer Support — CLI Orchestrator

Usage:
  python main.py --lab all           # Run all labs in sequence (1 → 6)
  python main.py --lab 1             # Run only Lab 1
  python main.py --lab 1 2 3         # Run Labs 1, 2, and 3
  python main.py --cleanup           # Run cleanup (delete all AWS resources)
  python main.py --cleanup --dry-run # Preview cleanup without deleting
  python main.py --prereq            # Run prerequisite infrastructure setup only
"""
import argparse
import os
import subprocess
import sys
import time


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║    AgentCore Customer Support — Automated Python Project     ║
║    Prototype → Production on AWS Bedrock AgentCore           ║
╚══════════════════════════════════════════════════════════════╝
"""

LAB_DESCRIPTIONS = {
    1: "Prototype Agent    — Sync Knowledge Base, run local agent with 4 tools",
    2: "AgentCore Memory   — Persistent customer memory across sessions",
    3: "Gateway & Identity — Shared MCP tools via JWT-secured gateway",
    4: "Runtime Deployment — Containerized agent on managed AgentCore Runtime",
    5: "Frontend           — Streamlit chat interface with Cognito auth",
    6: "Observability      — OpenTelemetry tracing to CloudWatch GenAI dashboard",
}


def step(msg: str) -> None:
    print(f"\n{'=' * 64}")
    print(f"  {msg}")
    print(f"{'=' * 64}")


def run_prereq() -> None:
    """Run the prerequisite shell script to deploy CloudFormation stacks."""
    step("PREREQUISITE: Deploying CloudFormation infrastructure")
    print("\n[Step 1/1] Running scripts/prereq.sh...")
    print("  This deploys: S3 bucket, Lambda functions, DynamoDB tables, IAM roles")
    print("  and uploads Lambda code + DDGS layer to S3.\n")
    env = os.environ.copy()
    env.setdefault("AWS_REGION", "us-east-1")
    env.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    result = subprocess.run(["bash", "scripts/prereq.sh"], check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError("scripts/prereq.sh failed. Check the output above for details.")
    print("\n  Prerequisites deployed successfully.")


def run_lab(lab_num: int) -> None:
    """Import and run the specified lab module."""
    start = time.time()
    step(f"LAB {lab_num}: {LAB_DESCRIPTIONS[lab_num]}")

    if lab_num == 1:
        from agentcore.lab1_agent import run
    elif lab_num == 2:
        from agentcore.lab2_memory import run
    elif lab_num == 3:
        from agentcore.lab3_gateway import run
    elif lab_num == 4:
        from agentcore.lab4_runtime import run
    elif lab_num == 5:
        from agentcore.lab5_frontend import run
    elif lab_num == 6:
        from agentcore.lab_observability import run
    else:
        raise ValueError(f"Unknown lab number: {lab_num}")

    run()
    elapsed = time.time() - start
    print(f"\n  Lab {lab_num} finished in {elapsed:.0f}s.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AgentCore Customer Support — automated lab runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--lab",
        nargs="+",
        metavar="N",
        help="Lab number(s) to run (1-5), or 'all'",
    )
    group.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all project AWS resources",
    )
    group.add_argument(
        "--prereq",
        action="store_true",
        help="Run prerequisite infrastructure setup only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --cleanup: preview resources to delete without deleting",
    )
    parser.add_argument(
        "--skip-prereq",
        action="store_true",
        help="Skip prerequisite infrastructure check before running labs",
    )

    args = parser.parse_args()

    print(BANNER)

    overall_start = time.time()

    try:
        if args.prereq:
            run_prereq()

        elif args.cleanup:
            step("CLEANUP: Delete all project AWS resources")
            from agentcore.lab6_cleanup import run
            run(dry_run=args.dry_run)

        else:
            # --lab N [N ...]
            lab_args = args.lab
            if lab_args == ["all"]:
                labs_to_run = [1, 2, 3, 4, 5, 6]
            else:
                try:
                    labs_to_run = sorted(set(int(n) for n in lab_args))
                except ValueError:
                    parser.error("--lab expects integers 1-6 or 'all'")

            invalid = [n for n in labs_to_run if n not in range(1, 7)]
            if invalid:
                parser.error(f"Invalid lab numbers: {invalid}. Valid range: 1-6.")

            # Run prereq automatically before Lab 1 unless skipped
            if 1 in labs_to_run and not args.skip_prereq:
                run_prereq()

            for lab_num in labs_to_run:
                run_lab(lab_num)

        elapsed = time.time() - overall_start
        print(f"\n{'=' * 64}")
        print(f"  All done! Total time: {elapsed:.0f}s")
        print(f"{'=' * 64}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
