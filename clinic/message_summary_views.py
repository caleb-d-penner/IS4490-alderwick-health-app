from django.shortcuts import render

from . import gemini
from .message_summaries import MessageSummaryError, group_thread_summaries, summarize_threads


def message_summary_report(request, threads, *, template_name, thread_url_name):
    threads = list(threads.select_related("assigned_provider").prefetch_related("messages"))
    report_groups = []
    error = None
    report_generated = False

    if request.method == "POST":
        try:
            summaries = summarize_threads(threads)
        except (gemini.GeminiError, MessageSummaryError) as exc:
            error = str(exc)
        else:
            report_groups = group_thread_summaries(threads, summaries)
            report_generated = True

    return render(
        request,
        template_name,
        {
            "error": error,
            "report_generated": report_generated,
            "report_groups": report_groups,
            "thread_count": len(threads),
            "thread_url_name": thread_url_name,
        },
    )
