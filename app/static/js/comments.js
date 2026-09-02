document.addEventListener(
    "DOMContentLoaded",
    () => {

        if (!requireAuth()) {
            return;
        }

        if (!window.CURRENT_TICKET_ID) {
            return;
        }

        loadComments();

        const form =
            document.getElementById(
                "commentForm"
            );

        if (form) {
            form.addEventListener(
                "submit",
                addComment
            );
        }
    }
);


async function loadComments() {

    const body =
        document.getElementById(
            "commentsList"
        );

    if (!body) {
        return;
    }

    try {

        const data = await API.request(
            APP_CONFIG.ENDPOINTS.comments(
                CURRENT_TICKET_ID
            )
        );

        const comments =
            data.comments || [];


        body.innerHTML =
            comments.map(comment => {

                const name =
                    comment.User_Name
                    ||
                    comment.User_Email
                    ||
                    "User";


                const role =
                    comment.User_Role
                    ||
                    "employee";


                const createdAt =
                    comment.Created_At
                    ||
                    "";


                return `
                    <div class="comment-item">

                        <div class="comment-head">

                            <div>

                                <strong>
                                    ${esc(name)}
                                </strong>

                                <span class="chip">
                                    ${esc(role)}
                                </span>

                            </div>


                            <small class="muted">
                                ${esc(createdAt)}
                            </small>

                        </div>


                        <p>
                            ${esc(comment.Comment_Text)}
                        </p>

                    </div>
                `;

            }).join("")
            ||
            `
                <p class="muted">
                    No comments yet.
                </p>
            `;

    }
    catch (e) {

        body.innerHTML = `
            <p class="muted">
                ${esc(e.message)}
            </p>
        `;
    }
}


async function addComment(e) {

    e.preventDefault();


    const input =
        document.getElementById(
            "commentText"
        );


    const text =
        input.value.trim();


    if (!text) {

        toast(
            "Please write a comment",
            "error"
        );

        return;
    }


    try {

        await API.request(
            APP_CONFIG.ENDPOINTS.comments(
                CURRENT_TICKET_ID
            ),
            {
                method: "POST",

                body: JSON.stringify({
                    text: text
                })
            }
        );


        input.value = "";


        toast(
            "Comment added successfully"
        );


        await loadComments();

    }
    catch (e) {

        toast(
            e.message,
            "error"
        );
    }
}