<script>
    import {userStore, serverList} from "$lib/userStore";
</script>

<style>
    .content {
        margin-inline: auto;
        max-width: 72ch;
    }
</style>

<div class="content">
    {#if $userStore}
        <h1>Welcome {$userStore.username} to Miscord!</h1>
        <p>Here is a list of groups that you're a member of:</p>
        {#if $serverList}
            <ul>
                {#if $serverList.length === 0}
                    <li>None! Find invite codes from your friends or create your own!</li>
                {/if}
                {#each $serverList as server}
                    <li>
                        <a href="/chat/{server.id}">{server.name}</a>
                    </li>
                {/each}
                <li>
                    <a href="/chat/create">+: Create your own...</a>
                </li>
                <li>
                    <a href="/chat/join">+: Join using invite code...</a>
                </li>
            </ul>
        {:else}
            <ul>
                <li>Loading...</li>
            </ul>
        {/if}
    {:else}
        <h1>Miscord</h1>

        <p>
            You need to have an account to access the marvelous world of Miscord!
        </p>

        <p>
            Please create an account <a href="/register">here</a>, or log into your
            existing account <a href="/login">here</a>!
        </p>
    {/if}
</div>
