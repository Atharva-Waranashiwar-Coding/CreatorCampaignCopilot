import { useState } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Textarea } from "../ui/textarea";
import { ApiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { CollaborationComment } from "../../lib/types";

type ThreadedCommentsCardProps = {
  eyebrow: string;
  title: string;
  description: string;
  comments: CollaborationComment[];
  emptyMessage: string;
  placeholder: string;
  isLoading: boolean;
  isSubmitting: boolean;
  error: unknown;
  onCreate: (payload: { body: string; parent_comment_id: number | null }) => Promise<unknown>;
};

export function ThreadedCommentsCard({
  eyebrow,
  title,
  description,
  comments,
  emptyMessage,
  placeholder,
  isLoading,
  isSubmitting,
  error,
  onCreate,
}: ThreadedCommentsCardProps) {
  const [body, setBody] = useState("");
  const [replyTargetId, setReplyTargetId] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");

  const commentCount = countComments(comments);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-3 text-sm text-muted-foreground">{description}</p>
        </div>
        <Badge tone="muted">{commentCount} comments</Badge>
      </div>

      <div className="mt-5 rounded-[1.25rem] border border-border bg-white/80 p-4">
        <Textarea
          className="min-h-[120px]"
          placeholder={placeholder}
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Mention teammates with @email
          </p>
          <Button
            disabled={isSubmitting || !body.trim()}
            onClick={async () => {
              await onCreate({ body: body.trim(), parent_comment_id: null });
              setBody("");
            }}
          >
            {isSubmitting ? "Posting..." : "Add comment"}
          </Button>
        </div>
      </div>

      <MutationFeedback error={error} />

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading thread...</p>
      ) : comments.length ? (
        <div className="mt-6 space-y-4">
          {comments.map((comment) => (
            <CommentNode
              key={comment.id}
              comment={comment}
              depth={0}
              isSubmitting={isSubmitting}
              onReply={async (payload) => {
                await onCreate(payload);
                setReplyTargetId(null);
                setReplyBody("");
              }}
              onToggleReply={(commentId) => {
                setReplyTargetId((current) => (current === commentId ? null : commentId));
                setReplyBody("");
              }}
              replyBody={replyTargetId === comment.id ? replyBody : ""}
              replyTargetId={replyTargetId}
              setReplyBody={setReplyBody}
            />
          ))}
        </div>
      ) : (
        <p className="mt-6 rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </p>
      )}
    </Card>
  );
}

function CommentNode({
  comment,
  depth,
  isSubmitting,
  onReply,
  onToggleReply,
  replyBody,
  replyTargetId,
  setReplyBody,
}: {
  comment: CollaborationComment;
  depth: number;
  isSubmitting: boolean;
  onReply: (payload: { body: string; parent_comment_id: number | null }) => Promise<unknown>;
  onToggleReply: (commentId: number) => void;
  replyBody: string;
  replyTargetId: number | null;
  setReplyBody: (value: string) => void;
}) {
  const isReplying = replyTargetId === comment.id;

  return (
    <div className={depth ? "ml-4 border-l border-border/70 pl-4 md:ml-6 md:pl-5" : ""}>
      <div className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-medium text-foreground">{comment.author_name ?? "Unknown user"}</p>
          <Badge tone="muted">{formatDateTime(comment.created_at)}</Badge>
          {comment.replies.length ? <Badge tone="muted">{comment.replies.length} replies</Badge> : null}
        </div>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">{comment.body}</p>
        {comment.mentions.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {comment.mentions.map((mention) => (
              <Badge key={mention.id} tone="default">
                @{mention.mentioned_user_email}
              </Badge>
            ))}
          </div>
        ) : null}
        <div className="mt-4">
          <Button onClick={() => onToggleReply(comment.id)} variant="ghost">
            {isReplying ? "Cancel reply" : "Reply"}
          </Button>
        </div>
        {isReplying ? (
          <div className="mt-4 rounded-[1.1rem] border border-border bg-slate-50/80 p-4">
            <Textarea
              className="min-h-[96px]"
              placeholder="Reply to this thread. Use @email for mentions."
              value={replyBody}
              onChange={(event) => setReplyBody(event.target.value)}
            />
            <div className="mt-3 flex justify-end">
              <Button
                disabled={isSubmitting || !replyBody.trim()}
                onClick={() => onReply({ body: replyBody.trim(), parent_comment_id: comment.id })}
              >
                {isSubmitting ? "Posting..." : "Post reply"}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      {comment.replies.length ? (
        <div className="mt-4 space-y-4">
          {comment.replies.map((reply) => (
            <CommentNode
              key={reply.id}
              comment={reply}
              depth={depth + 1}
              isSubmitting={isSubmitting}
              onReply={onReply}
              onToggleReply={onToggleReply}
              replyBody={replyTargetId === reply.id ? replyBody : ""}
              replyTargetId={replyTargetId}
              setReplyBody={setReplyBody}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MutationFeedback({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error.message}
    </p>
  );
}

function countComments(comments: CollaborationComment[]): number {
  return comments.reduce((total, comment) => total + 1 + countComments(comment.replies), 0);
}
